# Development Priorities

> **Game Vision:** You are the **Owner**. Hire your GM and Head Coach, manage team finances, and build a dynasty. Your football decisions flow through the people you hire—choose wisely.

## Completed Milestones
- ✅ **Milestone 1:** Game Cycle (stage-based progression)
- ✅ **Milestone 2:** Salary Cap & Contracts
- ✅ **Milestone 3:** Player Progression & Regression
- ✅ **Milestone 4:** Statistics & Record Keeping
- ✅ **Milestone 5:** Injuries & IR System (106 tests passing)
- ✅ **Milestone 6:** Trade System (Players + Draft Picks, 62 tests passing)
  - AI GM-managed trades (user does not directly propose trades)
  - Trade deadline countdown in status bar (weeks 7-9)
  - Trade history view (read-only)
  - AI evaluation with accept/reject/counter decisions
  - Future: Owner directs GM to pursue specific trades (#27 Front Office Direction)
- ✅ **Milestone 7:** Player Personas & Preferences (79 tests passing)
  - 8 persona types (Ring Chaser, Hometown Hero, Money First, etc.)
  - PlayerPreferenceEngine for scoring team attractiveness
  - Re-signing integration with persona-based decisions
  - Trade veto logic based on player preferences
  - UI: Interest column in Free Agency, Signing Dialog with persona details
- ✅ **Milestone 8:** Team Statistics (52 tests passing)
  - TeamSeasonStatsAPI with offensive/defensive/special teams aggregation
  - BoxScoresAPI with game-level team stats persistence
  - TeamStatsService combining stats, standings, and rankings
  - UnifiedDatabaseAPI integration (4 new methods)
  - UI: Team Stats tab with Offense/Defense/Turnovers views
- ✅ **Milestone 9:** Realistic Game Scenarios (All 7 Tollgates Complete)
  - Clock Management: Timeout tracking, play duration, strategic usage
  - Two-Minute Drill: Spike plays, hurry-up tempo, out-of-bounds awareness
  - Game Script Enforcement: Play calling adapts to score/time (control game, desperation)
  - Prevent Defense: Late-game defensive adjustments when protecting leads
  - Momentum & Flow: Recent plays affect subsequent outcomes (±5% performance)
  - Environmental Modifiers: Weather, crowd noise, clutch performance, primetime variance
  - Variance & Unpredictability: Hot/cold streaks, execution variance, rare events
- ✅ **Milestone 10:** Awards System (MVP, All-Pro, Pro Bowl)
  - Award candidates with eligibility checking (games played, snaps, position)
  - Position-specific scoring for MVP, OPOY, DPOY, OROY, DROY, CPOY
  - All-Pro team selection (First Team + Second Team by position)
  - Pro Bowl roster selection (AFC/NFC, fallback handling)
  - Statistical Leaders tracking (passing, rushing, receiving, sacks, INTs)
  - Awards View UI with tabbed navigation
- ✅ **Milestone 11:** Schedule & Rivalries (All 8 Tollgates Complete, 297+ tests)
  - Rivalry system: Division, historic, geographic, recent rivalry types
  - Head-to-head history tracking with streak calculation
  - Bye week scheduling (weeks 5-14, max 6 teams per week)
  - Primetime scheduling: TNF, SNF, MNF with matchup appeal scoring
  - Rivalry gameplay effects: Performance modifiers, penalty variance, crowd boost
  - Dynamic rivalry evolution: Intensity changes based on game outcomes
  - Schedule UI with rivalry indicators and primetime badges
  - Flex scheduling: Late-season primetime adjustments based on playoff implications
- ✅ **Milestone 12:** Media Coverage (All 7 Tollgates Complete)
  - Database schema for power_rankings, media_headlines, narrative_arcs, press_quotes
  - MediaCoverageAPI with full CRUD operations
  - PowerRankingsService with weighted algorithm and tier classification
  - HeadlineGenerator with 200+ templates across 12 event types
  - Game recap narratives with 4-paragraph body text generation
  - Award race coverage (MVP Watch, Rookie Watch, predictions)
  - ESPN-style UI with scoreboard ticker, breaking news banner, featured headlines
- ✅ **Milestone 14:** Contract Valuation Engine (All 9 Tollgates Complete, 219 tests)
  - Multi-factor valuation: stats, scouting grades, market comparables, overall rating, age
  - GM personality-driven weighting (analytics_heavy, scout_focused, balanced, market_driven)
  - Owner pressure modifiers (job security affects overpay/discount behavior)
  - Position-specific market rates calibrated to 2024 NFL contracts
  - Full audit trail with ValuationResult dataclass for benchmarking
  - UI Integration: ValuationBreakdownWidget with collapsible factor details
  - Integrated into GMProposalNotificationDialog, SigningDialog, ContractDetailsDialog
- ✅ **Milestone 13:** Owner-GM Offseason Flow (All 12 Tollgates Complete, 184+ tests)
  - Owner Review UI: OffseasonDirectiveDialog for setting philosophy, budget stance, position priorities
  - GM Proposal System: ProposalAPI, PersistentGMProposal with approval workflow
  - Full integration across all offseason stages: Franchise Tag, Re-signing, FA, Trading, Draft, Roster Cuts, Waiver Wire
  - Trust GM mode for auto-approval, batch approval dialogs
  - Staff management: Fire/hire GM and Head Coach from procedurally generated candidates
  - Persistent directives database with season-over-season tracking

## In Progress
- 🔄 **Free Agency Depth** (Tollgates 1-5 Complete, 165 tests)
  - 5-wave system: Legal Tampering → Elite → Quality → Depth → Post-Draft
  - Database schema: pending_offers, fa_wave_state tables
  - FAWaveService with wave progression and offer lifecycle
  - FAWaveExecutor orchestrator with result dataclasses
  - UI wave display with status indicators
  - Pending: Tollgate 6 (Offer Dialog), Tollgate 7 (Integration Testing)

## Next Up

- **Advanced Analytics & PFF Grades** (Deferred)
  - Per-play grades (0-100 scale) for every player
  - Advanced offensive metrics: EPA, Success Rate, Air Yards, YAC, Pressure Rate
  - Advanced defensive metrics: Pass Rush Win Rate, Coverage Grade, Missed Tackle Rate
  - Position-specific grades integrated with Awards and Scouting systems

---

## Priority Roadmap

### Core Simulation (Must Have)
| # | Milestone | Status | Dependencies |
|---|-----------|--------|--------------|
| 1 | Player Progression & Regression | ✅ Complete | Training Camp (done) |
| 2 | Statistics & Record Keeping | ✅ Complete | Game engine (done) |
| 3 | Advanced Analytics & PFF Grades | Not Started | Stats |
| 4 | Injuries & IR System | ✅ Complete | Stats |
| 5 | Trade System | ✅ Complete | Cap (done), Stats (done) |
| 6 | Player Personas & Preferences | ✅ Complete | None |
| 7 | Free Agency Depth | 🔄 In Progress (T1-5) | Player Personas, Cap (done) |
| 8 | Team Statistics | ✅ Complete | Stats (done), Game Engine |

### Simulation Realism
| #  | Milestone                   | Status      | Dependencies          |
|----|-----------------------------|--------------|-----------------------|
| 9  | Realistic Game Scenarios    | ✅ Complete | Stats, Progression    |
| 10 | Awards System (MVP, All-Pro)| ✅ Complete | Stats, Analytics      |
| 11 | Schedule & Rivalries        | ✅ Complete | None                  |
| 12 | Media Coverage              | ✅ Complete | Stats, Awards         |
| 13 | Draft Class Variation       | Not Started | Stats                 |
| 14 | Social Media & Fan Reactions| Not Started | Stats, Transactions   |
| 15 | Player Popularity           | Not Started | Stats, Awards, Media  |
| 16 | Press Conferences           | Not Started | Media, Coach/GM AI    |

### Legacy & History
| #  | Milestone                   | Status      | Dependencies          |
|----|-----------------------------|--------------|-----------------------|
| 17 | Player Retirements          | Not Started | Stats, Progression    |
| 18 | Hall of Fame                | Not Started | Retirements, Awards   |
| 19 | Team History & Records      | Not Started | Stats                 |
| 20 | NFL Records                 | Not Started | Stats                 |

### Coaching & Management
| #  | Milestone               | Status      | Dependencies         |
|----|-------------------------|-------------|----------------------|
| 21 | Head Coaching System    | Not Started | Game Scenarios       |
| 22 | Coaching Staff & Hiring | Not Started | Head Coaching        |
| 23 | Playcalling & Schemes   | Not Started | Head Coaching        |
| 24 | Scouting System         | Not Started | Draft Class, Analytics|

### Ownership & Business
| #  | Milestone                  | Status      | Dependencies              |
|----|----------------------------|-------------|---------------------------|
| 13 | **Owner-GM Offseason Flow**| ✅ Complete | FA Depth, Trades, Cap (done) |
| 25 | Owner Communication Portal | Partial*    | None                      |
| 26 | GM Hiring & Firing         | ✅ Complete*| Owner-GM Flow             |
| 27 | Coach Hiring & Firing      | ✅ Complete*| Owner-GM Flow             |
| 28 | Roster Management          | Not Started | Coach AI                  |
| 29 | Front Office Direction     | ✅ Complete*| Owner-GM Flow             |
| 30 | Season Goals               | Partial*    | GM Behaviors, Coach AI    |
| 31 | Stadium & Pricing          | Not Started | None                      |
| 32 | Team Finances (P&L)        | Not Started | Stadium, Cap              |
| 33 | Business Dashboards        | Not Started | Finances, Stadium         |
| 34 | Revenue Streams            | Not Started | Finances, Media, Social, Popularity |
| 35 | Team Valuation             | Not Started | Finances, Stats           |
| 36 | Marketing & Promotions     | Not Started | Revenue, Social, Media    |

*Addressed by Owner-GM Offseason Flow (Milestone 13) — includes GM/HC firing/hiring, directives, proposal approval workflow

### Intelligence Layer
| #  | Milestone                    | Status      | Dependencies                         |
|----|------------------------------|-------------|--------------------------------------|
| 37 | GM Behaviors & Team Building | Not Started | Stats, Trades, Progression, Scouting, Analytics |
| 38 | Coach AI & Game Management   | Not Started | Head Coaching, Game Scenarios        |
| 39 | Market Dynamics              | Not Started | Stats, GM Behaviors, Media           |
| 40 | **Contract Valuation Engine**| ✅ Complete | Stats, Owner Review, GM Archetypes   |

### Tools & Utilities
| #  | Milestone                   | Status      | Dependencies          |
|----|-----------------------------|--------------|-----------------------|
| 41 | CSV Export                  | Not Started | Stats (done)          |
| 42 | League Settings             | Not Started | None                  |

---

## Dependency Flow

```
        ┌─────────────────────────────────────────────────────────────────────┐
        │                         OWNER LAYER                                 │
        │  24. GM Hire    25. Coach Hire    26. Roster    27. Front Office    │
        │       │               │               │               │             │
        │       │               │               │     ┌─────────┘             │
        │       ▼               ▼               ▼     ▼                       │
        │  35. GM Behaviors ◄───────────────────┴─────┘                       │
        │       ▲               ▼                                             │
        │       │         36. Coach AI ◄──────────────── 26. Roster Mgmt      │
        │       │               ▲                                             │
        │       └───────────────┴──────────── 28. Season Goals                │
        └─────────────────────────────────────────────────────────────────────┘
                   │                    │
        ┌──────────┼────────────────────┼─────────────────────────────────────┐
        │          ▼                    ▼                                     │
        │  1. Progression ✅ ──► 9. Game Scenarios ✅ ──► 21. Head Coaching     │
        │  2. Statistics ✅ ──► 3. Analytics ──► 10. Awards ✅ ──► 15. Popularity │
        │       │         ──► 17. Retirements ──► 18. Hall of Fame    │       │
        │       └─────────────► 19. Team History    20. NFL Records   ▼       │
        │  4. Injuries ✅ ──► 13. Draft Class ──► 24. Scouting   14. Social   │
        │  5. Trades ✅         │                │                            │
        │  6. Personas ✅ ──► 7. FA Depth        │                            │
        │ 11. Schedule ✅       │  12. Media ✅ + 37/38 AI ──► 16. Press Conf  │
        │                       └────────────────┴──► 37. GM Behaviors        │
        │                                           39. Market Dynamics       │
        │                          FOOTBALL SIMULATION                        │
        └─────────────────────────────────────────────────────────────────────┘
                                           │
        ┌──────────────────────────────────┼──────────────────────────────────┐
        │                                  ▼                                  │
        │  29. Stadium ──► 30. Finances ──► 31. Dashboards                    │
        │       │                │               │                            │
        │       └────────────────┴───► 32. Revenue ◄── 13. Social + 14. Pop   │
        │                                   │                                 │
        │                    33. Valuation ◄┴──► 34. Marketing                │
        │                          BUSINESS LAYER                             │
        └─────────────────────────────────────────────────────────────────────┘
```

---

## Guiding Principles

1. **You are the Owner** — Football decisions flow through people you hire (GM, Coach)
2. **Core mechanics first** — AI decisions are only as good as the systems they operate on
3. **Football drives business** — Winning affects revenue, valuation, and fan engagement

---

## Feature Details

### Owner-GM Offseason Flow (✅ COMPLETE)

A unified system that enables the Owner to set direction, then let the GM automate offseason decisions with approval checkpoints. Combines elements of #25 (Owner Communication Portal), #29 (Front Office Direction), #30 (Season Goals), and #37 (GM Behaviors).

**Design Philosophy:**
- Owner is **NOT** the GM — you set direction, not execute transactions
- GM proposes, Owner approves — every significant move requires sign-off
- Automation with oversight — skip the tedium, keep the control

**Offseason Stage Flow with Owner-GM Interaction:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        OFFSEASON FLOW                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PHASE 1: OWNER REVIEW (One-Time Setup at Offseason Start)                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Owner sets offseason priorities:                                    │   │
│  │  • Team Philosophy: Win-Now / Rebuild / Maintain                     │   │
│  │  • Budget Stance: Aggressive / Moderate / Conservative               │   │
│  │  • Position Priorities: "We need a WR1" / "Shore up O-line"          │   │
│  │  • Protected Players: "Don't trade Player X"                         │   │
│  │  • Expendable Players: "Open to moving Player Y"                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↓                                              │
│  PHASE 2: GM AUTOMATION (Per-Stage with Approval Gates)                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  HONORS ──────────► (Automated, no approval needed)                   │   │
│  │                                                                       │   │
│  │  FRANCHISE TAG ───► GM proposes tag candidate ──► Owner approves     │   │
│  │                                                                       │   │
│  │  RE-SIGNING ──────► GM proposes extensions ──────► Owner approves    │   │
│  │                                                                       │   │
│  │  FREE AGENCY ─────► GM proposes signings ────────► Owner approves    │   │
│  │                     (Multiple waves, batched proposals)               │   │
│  │                                                                       │   │
│  │  TRADING ─────────► GM proposes trades ──────────► Owner approves    │   │
│  │                                                                       │   │
│  │  DRAFT ───────────► GM proposes picks ───────────► Owner approves    │   │
│  │                     (Per-round or per-pick based on preference)       │   │
│  │                                                                       │   │
│  │  ROSTER CUTS ─────► GM proposes cuts ────────────► Owner approves    │   │
│  │                                                                       │   │
│  │  WAIVER WIRE ─────► GM proposes claims ──────────► Owner approves    │   │
│  │                                                                       │   │
│  │  TRAINING CAMP ───► (Automated progression, no approval needed)       │   │
│  │                                                                       │   │
│  │  PRESEASON ───────► (Automated games, no approval needed)             │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Implementation Tollgates:**

| Tollgate | Description | Key Deliverables |
|----------|-------------|------------------|
| **T1** | Owner Review UI | OffseasonDirectiveDialog, priority sliders, position needs selector |
| **T2** | Directive Data Model | `offseason_directives` table, OffseasonDirective dataclass |
| **T3** | GM Proposal System | GMProposal dataclass, ProposalAPI, proposal generation logic |
| **T4** | Approval UI | ProposalReviewDialog with Accept/Reject/Modify actions |
| **T5** | Franchise Tag Integration | GM analyzes roster, proposes tag candidate with reasoning |
| **T6** | Re-signing Integration | GM prioritizes extensions based on directives, batched proposals |
| **T7** | Free Agency Integration | GM targets players matching needs, multi-wave proposal batches |
| **T8** | Trade Integration | GM seeks trade partners, presents packages with analysis |
| **T9** | Draft Integration | GM builds draft board influenced by directives, pick-by-pick or batch |
| **T10** | Roster Cuts Integration | GM proposes cuts to reach 53-man roster |
| **T11** | Waiver Wire Integration | GM claims players fitting team needs |
| **T12** | End-to-End Testing | Full offseason simulation with approval flow |

**Core Data Structures:**

```python
@dataclass
class OffseasonDirective:
    dynasty_id: str
    season: int
    philosophy: TeamPhilosophy  # WIN_NOW, REBUILD, MAINTAIN
    budget_stance: BudgetStance  # AGGRESSIVE, MODERATE, CONSERVATIVE
    position_priorities: List[str]  # ["WR", "EDGE", "CB"]
    protected_player_ids: List[str]
    expendable_player_ids: List[str]
    notes: str  # Free-form owner instructions

@dataclass
class GMProposal:
    proposal_id: str
    dynasty_id: str
    stage: StageType
    proposal_type: ProposalType  # TAG, EXTENSION, SIGNING, TRADE, DRAFT_PICK, CUT, CLAIM
    subject_player_id: Optional[str]
    details: Dict  # Stage-specific details (contract terms, trade package, etc.)
    gm_reasoning: str  # Why GM is recommending this
    confidence: float  # 0-1 how strongly GM recommends
    status: ProposalStatus  # PENDING, APPROVED, REJECTED, MODIFIED
    owner_notes: Optional[str]  # Owner feedback if modified/rejected
```

**GM Reasoning Examples:**

| Stage | Proposal | GM Reasoning |
|-------|----------|--------------|
| Franchise Tag | Tag WR Marcus Johnson | "Johnson is our top playmaker (1,200 yds, 9 TDs). Tagging preserves negotiation window. Cost: $19.5M. Aligns with your Win-Now directive." |
| Re-signing | Extend CB Darius Williams, 4yr/$52M | "Williams (28) is a Pro Bowler in his prime. Market value ~$15M/yr. This deal is slightly below market and keeps him through age-31 season." |
| Free Agency | Sign EDGE Khalil Mack, 2yr/$28M | "You prioritized EDGE rusher. Mack (33) is older but elite. Short deal limits risk. Fills your biggest defensive need." |
| Trade | Trade Pick 1.24 for WR Tyreek Hill | "Acquiring Hill immediately upgrades your WR room. Fits Win-Now window. Giving up 1st-rounder is aggressive but you marked 'Aggressive' budget." |
| Draft | Select QB Caleb Williams, Pick 1.01 | "BPA at franchise-need position. Your current QB is 34 and declining. Williams has highest ceiling in class." |
| Roster Cut | Release RB James Conner | "Conner (30) has $8M cap hit, only $2M dead money. Younger backs on roster. Frees cap space for your FA targets." |

**Owner Actions on Proposals:**

| Action | Effect |
|--------|--------|
| **Approve** | GM executes the transaction immediately |
| **Approve All** | Batch-approve multiple proposals (e.g., all cuts) |
| **Reject** | GM does not execute; may propose alternative |
| **Modify** | Owner adjusts terms (e.g., "offer 3 years instead of 4") |
| **Defer** | Move to next stage; may revisit later |
| **Ask for Alternatives** | GM generates 2-3 alternative proposals |

**Hands-Off Mode:**
For owners who want to delegate entirely:
- Toggle "Trust GM" at Owner Review phase
- GM executes all decisions without approval gates
- End-of-offseason summary shows all moves made
- Can be toggled per-stage or for entire offseason

**Integration with Existing Systems:**
- Uses existing `fa_wave_service.py` for Free Agency mechanics
- Uses existing `trade_service.py` for trade evaluation
- Uses existing `resigning_service.py` for extension logic
- Uses existing `draft_service.py` for draft board and picks
- Uses existing `roster_cuts_service.py` for cut decisions
- Uses existing `waiver_service.py` for waiver claims

**UI Mockup - Owner Review:**
```
┌─────────────────────────────────────────────────────────────────┐
│  OFFSEASON DIRECTION - 2025                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TEAM PHILOSOPHY                                                │
│  ○ Win-Now   ● Maintain   ○ Rebuild                             │
│                                                                 │
│  SPENDING APPROACH                                              │
│  ○ Aggressive   ● Moderate   ○ Conservative                     │
│                                                                 │
│  POSITION NEEDS (drag to prioritize)                            │
│  ┌─────────────────────────────────┐                            │
│  │ 1. EDGE                         │                            │
│  │ 2. WR                           │                            │
│  │ 3. CB                           │                            │
│  └─────────────────────────────────┘                            │
│                                                                 │
│  PROTECTED PLAYERS                                              │
│  [Patrick Mahomes] [Travis Kelce] [+Add]                        │
│                                                                 │
│  EXPENDABLE PLAYERS                                             │
│  [Clyde Edwards-Helaire] [+Add]                                 │
│                                                                 │
│  NOTES TO GM                                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Focus on young players with upside. Don't overpay for   │   │
│  │ veterans over 30.                                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [ ] Trust GM (skip approval gates)                             │
│                                                                 │
│         [Cancel]                    [Set Direction →]           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**UI Mockup - Proposal Review:**
```
┌─────────────────────────────────────────────────────────────────┐
│  GM PROPOSAL - FREE AGENCY                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PROPOSED SIGNING                                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  EDGE  Khalil Mack (33)                                  │   │
│  │  Contract: 2 years, $28M ($14M AAV)                      │   │
│  │  Guaranteed: $20M                                        │   │
│  │  Cap Hit Year 1: $12M                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  GM REASONING                                                   │
│  "You prioritized EDGE rusher. Mack is a proven pass           │
│  rusher with 87 career sacks. The 2-year deal limits           │
│  risk given his age. Fills your #1 positional need."           │
│                                                                 │
│  GM CONFIDENCE: ████████░░ 80%                                  │
│                                                                 │
│  YOUR CAP SITUATION                                             │
│  Current Space: $32.5M → After Signing: $20.5M                 │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ [Approve] [Reject] [Modify Terms] [See Alternatives]     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  PENDING PROPOSALS: 3 more                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Dependencies:**
- Builds on completed: Salary Cap, Trades, FA Depth, Player Personas
- Minimal new infrastructure: Directive storage, Proposal workflow
- Reuses existing GM decision logic, just adds approval layer

**Why This Approach:**
1. **Delivers the Owner fantasy** — You're not doing paperwork, you're directing strategy
2. **Keeps the game moving** — No manual transaction-by-transaction tedium
3. **Adds meaningful decisions** — Approve/reject creates tension and consequences
4. **Scales to hands-off** — Trust GM mode for experienced players who want speed

---

### Advanced Analytics & PFF Grades (#3)

Comprehensive player grading system inspired by PFF, providing granular performance evaluation for every player on every play. Integrates with scouting for prospect evaluation.

**Core Concepts:**

- **Per-Play Grades** (0-100 scale):
  - Every play graded for every player involved
  - Grades account for context (down, distance, situation)
  - Positive plays (80+), neutral (60-79), negative (0-59)
  - Aggregated to game, season, and career grades

- **Advanced Offensive Metrics**:
  | Metric | Description |
  |--------|-------------|
  | EPA (Expected Points Added) | Points added/lost per play |
  | Success Rate | % of plays gaining positive EPA |
  | Air Yards | Passing yards before catch |
  | YAC (Yards After Catch) | Receiving yards after catch |
  | Pressure Rate | % of dropbacks under pressure |
  | Time to Throw | Average release time |
  | Completion % Over Expected | Actual vs. expected completions |

- **Advanced Defensive Metrics**:
  | Metric | Description |
  |--------|-------------|
  | Pass Rush Win Rate | % of pass rush snaps beating blocker |
  | Coverage Grade | Effectiveness in coverage |
  | Tackles For Loss | Tackles behind line of scrimmage |
  | Missed Tackle Rate | % of tackle attempts missed |
  | Forced Incompletions | Passes defended/broken up |
  | QB Hits | Hits on quarterback |

- **Position-Specific Grades**:
  - **QB**: Accuracy, decision-making, pocket presence, deep ball
  - **RB**: Vision, elusiveness, pass blocking, receiving
  - **WR/TE**: Route running, separation, contested catches, blocking
  - **OL**: Pass blocking, run blocking by position
  - **DL**: Pass rush, run defense, versatility
  - **LB**: Coverage, tackling, blitzing, run fits
  - **DB**: Man coverage, zone coverage, ball skills, tackling

- **Prospect Grades** (Scouting Integration):
  - College performance grades translated to pro projection
  - Athleticism vs. technique breakdown
  - Ceiling vs. floor projections
  - Position-specific prospect metrics
  - Combine/pro day results factored in

- **Grade Aggregation**:
  | Level | Calculation |
  |-------|-------------|
  | Play Grade | Raw 0-100 per snap |
  | Game Grade | Weighted average of play grades |
  | Season Grade | Weighted average of game grades (recent = more weight) |
  | Career Grade | Historical season grades with recency bias |

**Integration Points:**
- Depends on Statistics (#2) — Base stats feed advanced calculations
- Feeds into Awards (#9) — Grades influence All-Pro, MVP voting
- Feeds into Scouting (#23) — Prospect grades inform draft decisions
- Feeds into GM Behaviors (#35) — Analytics inform trade values, FA targets
- Feeds into Player Progression (#1) — Grades indicate development trajectory
- Affects Trade Value (#5) — Advanced metrics influence player worth

---

### Player Personas & Preferences (#6)

Each player has a unique persona and set of preferences that influence which teams they're likely to sign with in free agency, accept trades to, or take discounts for.

**Core Concepts:**
- **Player Personas**: Personality archetypes that define behavior
  - **Ring Chaser**: Prioritizes contenders, will take less money to win
  - **Hometown Hero**: Prefers team near birthplace/college, loyal to drafting team
  - **Money First**: Always follows the highest offer, no hometown discounts
  - **Big Market**: Wants LA, NYC, Dallas — media exposure and endorsements
  - **Small Market**: Prefers quieter markets, dislikes spotlight pressure
  - **Legacy Builder**: Wants to stay with one team, be a franchise icon
  - **Competitor**: Wants to play, avoids teams where they'd ride the bench
  - **System Fit**: Prioritizes schemes that match their skills

- **Team Preferences**: Factors that make teams more/less attractive
  - **Contender Status**: Recent playoff success, championship window
  - **Market Size**: Big market (endorsements) vs. small market (less pressure)
  - **Location**: Weather, proximity to family, state taxes
  - **Coaching Fit**: Coach's scheme matches player's strengths
  - **Role**: Starter vs. backup, featured vs. complementary
  - **Team Culture**: Winning culture, player-friendly organization
  - **Existing Relationships**: Former teammates, college connections

- **Preference Strength**: How much each factor matters (0-100)
  - Strong preferences create "must-have" requirements
  - Weak preferences are nice-to-have tiebreakers
  - Money can overcome most preferences (at the right price)

**Impact on Team Building:**
| Scenario | Player Behavior |
|----------|-----------------|
| FA Signing | Player ranks teams by preference match, may reject top offer |
| Trade Request | Player may demand trade to specific team(s) |
| Trade Veto | Player with no-trade clause blocks undesirable destinations |
| Contract Extension | Hometown discount for preferred team, premium for undesired |
| Draft Day | Prospects may publicly prefer/avoid certain teams |

**Preference Modifiers:**
- **Age**: Veterans more likely to be Ring Chasers
- **Career Earnings**: Players who've made $100M+ care less about money
- **Championships**: Players with 0 rings more desperate to win
- **Recent Performance**: Declining players accept backup roles
- **Family Situation**: Marriage/kids affect location preferences

**Integration Points:**
- Affects Free Agency Depth (#7) — Preferences drive player decisions in FA market
- Affects Trade System (#5) — Trade targets may veto destinations
- Connects to Social Media (#13) — Players tweet about preferred destinations
- Creates realistic market dynamics — Not every player goes to highest bidder

---

### Free Agency Depth (#7)

A multi-stage free agency market where players receive competing offers from multiple teams. Success requires understanding player preferences, market timing, and competitive positioning.

**Core Concepts:**

- **Free Agency Stages**:
  | Stage | Timing | Description |
  |-------|--------|-------------|
  | Legal Tampering | 2 days before FA | Teams can negotiate but not sign |
  | Wave 1 | FA opens | Top-tier players sign quickly |
  | Wave 2 | Days 3-7 | Mid-tier market develops |
  | Wave 3 | Week 2+ | Bargain hunting, remaining FAs |
  | Post-Draft | After draft | Final signings before camp |

- **Offer System**:
  - Teams submit offers with contract terms (years, $, guarantees)
  - Players collect offers over a decision window (1-3 days)
  - Player agent may counter-offer or request improvements
  - Bidding wars can escalate for top players

- **Player Decision Factors**:
  | Factor | Weight | Description |
  |--------|--------|-------------|
  | Money | High | Total value, guarantees, signing bonus |
  | Team Fit | Medium-High | Role, scheme fit, playing time |
  | Contender Status | Medium | Playoff history, championship window |
  | Location | Medium | Weather, family, taxes |
  | Relationships | Low-Medium | Former teammates, coaches |
  | Market Size | Low-Medium | Endorsement potential |

- **Market Dynamics**:
  - Top players sign quickly (Wave 1) - must act fast
  - Mid-tier players shop around - patience can win
  - Late-stage bargains - declining players take less
  - Positional runs - one signing triggers others

- **Uncertainty Mechanics**:
  | Scenario | Outcome |
  |----------|---------|
  | Outbid | Another team offers more money/years |
  | Preference Mismatch | Player prefers contender over your rebuilding team |
  | Surprise Signing | Player signs elsewhere without entertaining your offer |
  | Bidding War Won | You overpay to secure the player |
  | Bargain Found | Patient approach lands value signing |

**Integration Points:**
- Depends on Player Personas (#6) — Preferences drive player decisions
- Depends on Salary Cap (done) — Cap space limits offers
- Feeds into GM Behaviors (#35) — AI GMs compete using this system
- Feeds into Social Media (#13) — Fans react to signings/misses
- Creates roster building tension — Can't sign everyone you want

---

### Social Media & Fan Reactions (#13)

A dynamic social media feed that reflects fan sentiment about weekly games, transactions, and team decisions. Provides the Owner with immediate feedback on how their decisions are perceived.

**Core Concepts:**
- **Weekly Game Reactions**: Fan posts react to game outcomes
  - Blowout wins: Celebration, hype, playoff talk
  - Close wins: Relief, praise for clutch players
  - Close losses: Frustration, "we'll get 'em next time"
  - Blowout losses: Anger, calls for coaching changes, trade demands
  - Losing streaks: Growing unrest, #Fire[CoachName] trends
- **Transaction Reactions**: Fans respond to roster moves
  - Signing star FA: Excitement, championship expectations
  - Trading fan favorite: Outrage, questioning ownership
  - Cutting popular player: Sadness, nostalgia posts
  - Draft picks: Hope for rookies, analysis of value
  - Bad contracts: "Cap hell" complaints, GM criticism
- **Sentiment Meter**: Aggregate fan mood (0-100)
  - Affects stadium attendance (Revenue Streams #31)
  - Influences merchandise sales
  - Extreme negativity may affect player morale
- **Trending Topics**: Weekly hashtags based on events
  - #TankFor[Prospect] during losing seasons
  - #Dynasty during winning streaks
  - Player nicknames, game moments

**Post Types:**
| Event                  | Fan Reaction Examples                              |
|------------------------|---------------------------------------------------|
| Big Win                | "BEST TEAM IN THE LEAGUE!" / highlight clips      |
| Tough Loss             | "Fire the OC" / "We need a real QB"               |
| Star Signing           | "SUPER BOWL BOUND" / jersey purchase posts        |
| Controversial Trade    | "WORST GM EVER" / "Trust the process"             |
| Injury to Star         | "Season over" / get well wishes                   |
| Rookie Breakout        | "STEAL OF THE DRAFT" / hype videos                |

**Integration Points:**
- Depends on Statistics (#2) — Reactions reference player stats
- Depends on Transactions — Reacts to signings, trades, cuts
- Feeds into Revenue Streams (#32) — Fan engagement affects merch/tickets
- Connects to Media Coverage (#12) — Social amplifies media narratives

---

### Player Popularity (#14)

Individual player popularity tracking that measures how much fans care about specific players. Popular players drive merchandise sales, boost attendance, and generate media buzz.

**Core Concepts:**
- **Popularity Sources**:
  - **On-Field Performance**: Stats, highlight plays, clutch moments
  - **Awards & Accolades**: Pro Bowls, All-Pro, MVP votes boost visibility
  - **Media Exposure**: National TV games, interviews, features
  - **Social Media Presence**: Follower count, engagement, viral moments
  - **Marketability**: Personality, appearance, off-field brand
  - **Market Size**: Big market teams get more exposure

- **Star Power Rating** (0-100):
  - 90-100: Transcendent (jersey top-seller, moves ratings)
  - 75-89: Star (significant merch sales, attendance draw)
  - 50-74: Known (regional popularity, moderate impact)
  - 25-49: Role Player (known mainly to hardcore fans)
  - 0-24: Unknown (minimal fan recognition)

- **Popularity Effects**:
  | Star Power | Jersey Sales | Attendance Boost | Media Interest |
  |------------|--------------|------------------|----------------|
  | 90-100     | Top 5 seller | +5-10%           | National       |
  | 75-89      | Strong       | +2-5%            | Regional+      |
  | 50-74      | Moderate     | +1-2%            | Local          |
  | 25-49      | Minimal      | None             | Beat writers   |
  | 0-24       | None         | None             | None           |

- **Popularity Changes**:
  - Breakout games: +5-15 popularity
  - Awards: +10-20 popularity
  - Viral moments: +5-25 popularity (positive or negative)
  - Injuries/absence: -1-3 per week out of spotlight
  - Scandal/controversy: -10-50 popularity
  - Trade to big market: +5-15 popularity
  - Trade to small market: -5-10 popularity

**Integration Points:**
- Depends on Statistics (#2) — Performance drives popularity
- Depends on Awards (#9) — Accolades boost star power
- Depends on Media Coverage (#12) — Exposure builds popularity
- Feeds into Social Media (#13) — Popular players generate more buzz
- Feeds into Revenue Streams (#32) — Star power = merchandise sales
- Affects Attendance — Fans want to see popular players
- Affects Trade Value (#5) — Marketability adds business value beyond football

---

### Press Conferences (#15)

Interviews with the GM and Coach throughout the season, addressing hot topics like QB controversies, roster moves, injuries, and team performance. These bring your staff to life and show how they handle pressure.

**Core Concepts:**
- **Press Conference Types**:
  - **Weekly Game Pressers**: Post-game reactions from Coach
    - Analyzing the win/loss
    - Addressing player performance
    - Injury updates
  - **GM Availability**: Periodic interviews with GM
    - Trade deadline thoughts
    - Roster construction philosophy
    - Draft preview
  - **Special Pressers**: Triggered by major events
    - Star player injury announcements
    - Trade explanations
    - QB controversy responses
    - Firing/hiring announcements

- **Hot Topics Generated From Events**:
  - **QB Controversy**: Backup outperforms starter, or starter struggles
  - **Trade Rumors**: Media asks about rumored targets
  - **Injury Updates**: "What's the timeline on Player X?"
  - **Contract Situations**: "Will you extend Player Y?"
  - **Losing Streaks**: "Is Coach Z on the hot seat?"
  - **Playoff Push**: "What does the team need to make the playoffs?"

- **Response Styles by Archetype**:
  - **Confident Coach**: "We're focused on the next game"
  - **Fiery Coach**: "That's a ridiculous question"
  - **Diplomatic GM**: "We're always looking to improve"
  - **Honest GM**: "We need to add a pass rusher"
  - **Evasive**: "I'm not going to comment on rumors"

**Sample Press Conference Moments:**
| Situation              | Coach Response Example                                   |
|------------------------|----------------------------------------------------------|
| After Blowout Loss     | "We got outplayed. No excuses. We'll be better."         |
| QB Controversy         | "The starter is our guy. Period."                        |
| Star Injury            | "It's a significant injury. We'll know more tomorrow."   |
| Trade Deadline         | "We like our roster, but we're always looking."          |
| Playoff Clinch         | "Credit to the guys. They've worked hard for this."      |

**Integration Points:**
- Depends on Media Coverage (#12) — Media generates the questions
- Depends on Coach AI (#36) / GM Behaviors (#35) — Archetypes determine response style
- Feeds into Social Media (#13) — Fans react to press conference quotes
- Connects to Schedule & Rivalries (#10) — Pressers before/after big games

---

### Player Retirements (#16)

Players make retirement decisions based on age, performance decline, injuries, and career accomplishments. Retirements create emotional moments and roster turnover.

**Core Concepts:**
- **Retirement Triggers**:
  - Age + decline: Performance drops below threshold for position
  - Injury: Career-ending or lingering injury prompts early retirement
  - Championship: Some players retire after winning Super Bowl
  - Contract: Refuses to take paycut, chooses retirement over release
  - Personal: Random "family reasons" / "pursue other interests"
- **Retirement Ceremony**:
  - Press conference announcement
  - Final season farewell tour (if announced mid-season)
  - Jersey retirement consideration
  - One-day contracts to retire with original team
- **Career Summary Generated**:
  - Total stats, awards, championships
  - Team history and notable moments
  - Comparison to all-time greats
  - Hall of Fame projection

**Retirement Factors by Position:**
| Position | Typical Retirement Age | Key Decline Factors          |
|----------|------------------------|------------------------------|
| QB       | 38-42                  | Arm strength, mobility       |
| RB       | 28-32                  | Speed, durability            |
| WR       | 32-36                  | Speed, separation            |
| OL       | 34-38                  | Mobility, technique          |
| DL       | 32-36                  | Burst, stamina               |
| LB       | 32-35                  | Speed, coverage ability      |
| DB       | 32-36                  | Speed, reaction time         |
| K/P      | 38-45                  | Leg strength, accuracy       |

**Integration Points:**
- Depends on Statistics (#2) — Career stats inform retirement timing
- Depends on Progression (#1) — Decline triggers retirement consideration
- Feeds into Hall of Fame (#17) — Retired players become HOF candidates
- Creates roster needs — GM must plan for replacements

---

### Hall of Fame (#17)

Annual Hall of Fame voting for retired players, with realistic criteria based on career accomplishments, awards, and statistical achievements.

**Core Concepts:**
- **Eligibility**:
  - Must be retired for 5+ seasons
  - Career minimum thresholds (games played, stats)
- **Voting Criteria**:
  - Career statistics vs. position averages
  - Awards (MVP, All-Pro selections, Pro Bowls)
  - Championships (Super Bowl wins/appearances)
  - Longevity and consistency
  - Peak performance years
  - Era-adjusted comparisons
- **Voting Process**:
  - Annual ballot of eligible candidates
  - Simulated voter deliberation
  - 5 inductees maximum per year
  - First-ballot vs. multi-year candidates
- **Hall of Fame Weekend**:
  - Induction ceremony event
  - Speech highlights generated
  - Gold jacket presentation
  - Bust unveiling

**HOF Likelihood Factors:**
| Factor               | Weight | Example                              |
|----------------------|--------|--------------------------------------|
| MVP Awards           | High   | 2+ MVPs = near-lock                  |
| All-Pro Selections   | High   | 5+ First-Team = strong candidate     |
| Super Bowl Wins      | Medium | Ring(s) boost candidacy              |
| Career Stats         | Medium | Top 10 all-time at position          |
| Pro Bowl Selections  | Low    | Quantity matters less than quality   |
| Longevity            | Medium | 15+ year career shows durability     |

**Integration Points:**
- Depends on Player Retirements (#16) — Only retired players eligible
- Depends on Awards System (#9) — Awards factor into voting
- Connects to Team History (#18) — HOFers displayed in team history
- Creates legacy moments — Fans celebrate team's HOF inductees

---

### Team History & Records (#18)

Complete franchise history tracking including season records, playoff appearances, championships, and retired numbers.

**Core Concepts:**
- **Franchise Records**:
  - Single-game records (passing yards, rushing TDs, etc.)
  - Single-season records (4,000+ yard passers, 1,000+ yard rushers)
  - Career records (all-time passing leader, etc.)
  - Team records (most wins, longest win streak)
- **Season History**:
  - Year-by-year results (W-L record, playoff result)
  - Division titles, conference championships
  - Super Bowl wins/losses
  - Notable seasons (perfect regular season, worst record)
- **Retired Numbers**:
  - Jersey numbers retired for legendary players
  - Ring of Honor / Team Hall of Fame
  - Number retirement ceremony
- **Head-to-Head History**:
  - All-time record vs. each opponent
  - Rivalry records (vs. division foes)
  - Playoff matchup history
- **Coaching History**:
  - All-time coaches with records
  - Coaching tenures and achievements

**Team History Dashboard:**
| Section            | Contents                                        |
|--------------------|-------------------------------------------------|
| Championships      | Super Bowl wins, conference titles, division titles |
| Record Book        | Franchise records by category                   |
| Legends            | Retired numbers, HOFers, Ring of Honor          |
| Season Archive     | Year-by-year results, sortable/filterable       |
| Rivalries          | Head-to-head records vs. key opponents          |

**Integration Points:**
- Depends on Statistics (#2) — Stats populate records
- Connects to Hall of Fame (#17) — HOFers displayed in legends section
- Connects to Social Media (#13) — Fans reference history in posts
- Owner pride — See your dynasty's place in franchise history

---

### NFL Records (#19)

League-wide record tracking across all teams, including all-time statistical leaders, single-season records, and historical milestones.

**Core Concepts:**
- **All-Time Leaders**:
  - Career passing yards, touchdowns, interceptions
  - Career rushing yards, touchdowns
  - Career receiving yards, touchdowns, receptions
  - Career sacks, interceptions, tackles
  - Career field goals, punting average
- **Single-Season Records**:
  - Most passing yards/TDs in a season
  - Most rushing yards in a season
  - Most receiving yards in a season
  - Most sacks in a season
- **Single-Game Records**:
  - Most passing yards in a game
  - Most rushing TDs in a game
  - Most receptions in a game
- **Milestones Tracking**:
  - 500 career passing TDs
  - 20,000 career rushing yards
  - 15,000 career receiving yards
  - 200 career sacks
- **Record Chase Alerts**:
  - Notification when player approaches record
  - Media buzz as record is within reach
  - Celebration when record is broken

**NFL Record Categories:**
| Category      | Examples                                         |
|---------------|--------------------------------------------------|
| Passing       | Yards, TDs, completions, passer rating           |
| Rushing       | Yards, TDs, attempts, YPC                        |
| Receiving     | Yards, TDs, receptions, YPR                      |
| Defense       | Sacks, INTs, tackles, forced fumbles             |
| Special Teams | FG%, punt avg, kick return TDs                   |
| Team          | Most wins, points scored, point differential     |

**Integration Points:**
- Depends on Statistics (#2) — Stats are the foundation
- Connects to Media Coverage (#12) — Record chases generate headlines
- Connects to Social Media (#13) — Fans track record attempts
- Affects Player Value — Record holders command respect/contracts

---

### Scouting System (#23)

Scouts are hireable staff members who evaluate draft prospects. Their evaluations differ from true player ratings based on scout strengths and weaknesses.

**Core Concepts:**
- **Scout Strengths**: Each scout specializes in evaluating certain attributes/positions
  - Position specialists (e.g., "QB Guru", "Defensive Backs Expert")
  - Attribute specialists (e.g., "Physical Traits Analyst", "Football IQ Evaluator")
  - Regional scouts (better at evaluating players from specific colleges/regions)
- **Rating Variance**: Scouted ratings ≠ True ratings
  - Strong areas: Lower variance, closer to true rating (±2-5 points)
  - Weak areas: Higher variance, can miss or overvalue (±5-15 points)
  - Random element: Even great scouts occasionally miss
- **Scout Reports**: Generated evaluations that the GM uses for draft decisions
  - Confidence level based on scout strength match
  - Potential flags (bust risk, sleeper potential)

**Integration Points:**
- Feeds into GM Behaviors (#35) — GM draft decisions based on scout reports, not true ratings
- Depends on Draft Class Variation (#11) — Needs prospects with true ratings to scout
- Depends on Advanced Analytics (#3) — PFF-style prospect grades enhance scouting
- Owner hires/fires scouts as part of staff management

---

### Roster Management (#26)

The Owner cannot directly make roster moves. Instead, the Owner requests roster changes through the Coach, who may comply or push back based on their archetype and philosophy.

**Core Concepts:**
- **Request System**: Owner submits roster move requests to the Coach
  - "Start Player X over Player Y"
  - "Release Player Z"
  - "Activate Player from Practice Squad"
  - "Change depth chart positioning"
- **Coach Archetypes**: Determine how coaches respond to owner interference
  - **Yes-Man**: Always complies, never pushes back (easy but may not be best football decisions)
  - **Players' Coach**: Pushes back on moves that hurt player morale/veterans
  - **Old School**: Resists changes to starters, respects seniority
  - **Analytics-Driven**: Pushes back if data doesn't support the move
  - **My Way**: Strong pushback on all interference, threatens to quit if overruled repeatedly
- **Pushback Mechanics**:
  - Coach provides reasoning for disagreement
  - Owner can override (damages coach relationship)
  - Repeated overrides may trigger coach resignation or demand for firing
  - Some coaches may comply publicly but sabotage subtly (reduced effort)

**Request Outcomes:**
| Coach Response | Result |
|----------------|--------|
| Comply | Move executed immediately |
| Soft Pushback | Coach explains concerns, owner chooses to proceed or withdraw |
| Hard Pushback | Coach threatens consequences if overruled |
| Refuse | Coach won't execute (owner must fire coach to proceed) |

**Integration Points:**
- Depends on Coach AI (#36) — Coach archetypes determine pushback behavior
- Affects Coach Hiring/Firing (#25) — Repeated conflicts may end relationship
- Ties into Team Chemistry — Players notice when owner overrules coach

---

### Front Office Direction (#27)

The Owner cannot directly execute trades, sign free agents, or make draft picks. Instead, the Owner directs the GM, who may comply or push back based on their archetype. The Owner can also choose to be hands-off and let the GM operate autonomously.

**Core Concepts:**
- **Request System**: Owner submits personnel requests to the GM
  - "Pursue Player X in free agency"
  - "Trade for Player Y"
  - "Draft Player Z with our pick"
  - "Don't spend money this offseason" / "Go all-in this year"
- **GM Archetypes**: Determine how GMs respond to owner direction
  - **Loyal Soldier**: Always follows owner direction, even against better judgment
  - **Cap Wizard**: Pushes back on moves that hurt long-term cap health
  - **Draft-and-Develop**: Resists trading picks, pushes for patience
  - **Win-Now**: Eager to make splashy moves, may overspend
  - **Analytics GM**: Pushes back on moves that don't match value models
  - **Old Guard**: Trusts tape over numbers, may ignore owner's analytics requests
- **Hands-Off Mode**: Owner can delegate entirely to GM
  - GM operates based on their archetype and team needs
  - Owner reviews results but doesn't micromanage
  - Trust builds over time with success, erodes with failure
- **Pushback Mechanics**:
  - GM explains reasoning for disagreement
  - Owner can override (damages relationship, may affect GM effort)
  - Repeated overrides may trigger GM resignation or performance decline
  - Some GMs may execute poorly on moves they disagree with

**Request Outcomes:**
| GM Response    | Result                                                    |
|----------------|-----------------------------------------------------------|
| Comply         | GM executes the request to best of ability                |
| Soft Pushback  | GM presents concerns, owner chooses to proceed or defer   |
| Hard Pushback  | GM warns of consequences (cap hell, depleted roster)      |
| Refuse         | GM won't execute (owner must fire GM to proceed)          |

**Integration Points:**
- Depends on GM Behaviors (#35) — GM archetypes determine pushback and execution quality
- Affects GM Hiring/Firing (#24) — Repeated conflicts may end relationship
- Works with Season Goals (#28) — Goals provide context for GM decision-making

---

### Season Goals (#28)

At the start of each season, the Owner sets goals that influence how both the GM and Coach behave throughout the year. Goals create alignment (or tension) between owner expectations and staff actions.

**Core Concepts:**
- **Goal Types**:
  - **Win-Now**: "Make the playoffs" / "Win the Super Bowl"
    - GM prioritizes veterans, willing to trade picks
    - Coach plays starters more, takes fewer risks with young players
  - **Rebuild**: "Develop young talent" / "Accumulate draft picks"
    - GM trades veterans for picks, avoids expensive free agents
    - Coach plays rookies even in close games
  - **Financial**: "Stay under cap" / "Reduce payroll"
    - GM avoids big contracts, lets expensive players walk
    - May conflict with win-now goals
  - **Player Development**: "Get Player X to Pro Bowl level"
    - Coach adjusts scheme to feature target player
    - GM protects player in trade discussions
  - **Competitive**: "Beat Rival Team" / "Win the division"
    - Affects risk-taking in specific games
    - May influence roster moves targeting rival weaknesses

- **Goal Conflicts**:
  - Staff may push back if goals are contradictory
  - "Win now AND stay under cap" creates tension
  - GM/Coach alignment matters — misaligned archetypes cause friction

- **Goal Evaluation**:
  - End-of-season review compares results to goals
  - Success builds trust, unlocks staff loyalty bonuses
  - Failure creates pressure — owner may need to fire or adjust expectations
  - Unrealistic goals damage owner credibility with staff

**Staff Response to Goals:**
| Goal Alignment | Staff Behavior                                           |
|----------------|----------------------------------------------------------|
| Aligned        | Staff operates confidently, better execution             |
| Neutral        | Standard performance                                     |
| Conflicted     | Staff requests clarification, may underperform           |
| Impossible     | Staff warns owner, relationship damaged if forced        |

**Integration Points:**
- Affects GM Behaviors (#35) — Goals shape trade, FA, and draft priorities
- Affects Coach AI (#36) — Goals influence game-day decisions and player usage
- Ties into GM/Coach Hiring (#24, #25) — Staff hired for goal alignment
- Influences End-of-Season Reviews — Goals are the measuring stick

---

### Stadium & Pricing (#29)

The Owner controls stadium operations including ticket pricing, concession prices, and facility quality. Pricing decisions directly affect revenue but also fan satisfaction and attendance.

**Core Concepts:**
- **Ticket Pricing**: Set prices for different seating tiers
  - Premium/Suite: High-margin luxury seating
  - Club Level: Mid-tier with amenities
  - Upper Deck: Budget-friendly options
  - Standing Room: Maximize capacity on big games
- **Concession Pricing**: Set food and beverage prices
  - Beer, soda, hot dogs, premium items
  - Higher prices = more revenue per fan, but lower satisfaction
  - "Value Menu" options to balance accessibility
- **Dynamic Pricing**: Adjust based on opponent/demand
  - Rival games: Premium pricing
  - Weak opponents: Discounted to fill seats
  - Playoff games: Maximum pricing

**Pricing Trade-offs:**
| Strategy         | Revenue Impact | Fan Sentiment | Attendance |
|------------------|----------------|---------------|------------|
| Premium Pricing  | High per-fan   | Negative      | Lower      |
| Market Rate      | Balanced       | Neutral       | Normal     |
| Fan-Friendly     | Lower per-fan  | Positive      | Higher     |
| Dynamic          | Optimized      | Mixed         | Variable   |

**Integration Points:**
- Feeds into Team Finances (#30) — Pricing affects game-day revenue
- Affects Social Media (#13) — Fans react to price changes
- Connects to Business Dashboards (#31) — Track pricing effectiveness

---

### Business Dashboards (#31)

Real-time and historical dashboards showing key business metrics. The Owner can monitor attendance, viewership, and financial health at a glance.

**Core Concepts:**
- **Game Attendance Dashboard**:
  - Per-game attendance numbers
  - Season average vs. stadium capacity
  - Attendance trends (up/down vs. last season)
  - Sellout streak tracking
  - No-show rate (tickets sold vs. actual attendance)
- **TV Viewership Dashboard**:
  - Local market ratings
  - National broadcast appearances
  - Primetime game count
  - Streaming/digital viewership
  - Market share vs. competing entertainment
- **Financial Dashboard**:
  - Revenue by stream (tickets, concessions, merch, media)
  - Operating expenses
  - Profit/Loss by month and season
  - Cap space utilization
  - Year-over-year comparisons
- **Fan Engagement Metrics**:
  - Social media followers/engagement
  - Season ticket renewal rate
  - Waitlist size
  - Fan satisfaction scores

**Dashboard Views:**
| Dashboard        | Key Metrics                                          |
|------------------|------------------------------------------------------|
| Game Day         | Today's attendance, concession sales, weather impact |
| Season Overview  | Win %, attendance avg, revenue YTD                   |
| Fan Pulse        | Sentiment score, social mentions, trending topics    |
| Financial Health | P&L, cap space, revenue trends                       |

**Integration Points:**
- Depends on Stadium & Pricing (#29) — Shows pricing impact
- Depends on Team Finances (#30) — Financial data source
- Informs Marketing (#34) — Identify areas needing promotion

---

### Marketing & Promotions (#34)

A dedicated marketing department that runs promotional campaigns, sponsorship deals, and fan engagement initiatives. This is a later-stage feature for deeper business simulation.

**Core Concepts:**
- **Promotional Campaigns**:
  - Theme nights (Throwback Thursday, Kids Day)
  - Giveaways (bobbleheads, jerseys, hats)
  - Discounted ticket packages
  - Group sales initiatives
  - Holiday promotions
- **Sponsorship Deals**:
  - Stadium naming rights
  - Jersey patches
  - In-stadium advertising
  - Exclusive partnerships (beer, soft drinks, etc.)
  - Local business partnerships
- **Fan Programs**:
  - Loyalty rewards program
  - Season ticket holder perks
  - Youth football camps
  - Community outreach events
  - Player appearance programs

**Campaign Effectiveness:**
| Campaign Type    | Cost   | Attendance Boost | Revenue Impact | Fan Sentiment |
|------------------|--------|------------------|----------------|---------------|
| Bobblehead Night | Medium | +15-20%          | Neutral        | Very Positive |
| Discount Games   | Low    | +25-30%          | Negative       | Positive      |
| Premium Sponsor  | None*  | Minimal          | High           | Neutral       |
| Theme Night      | Low    | +10-15%          | Positive       | Positive      |
| Community Event  | Medium | Minimal          | Neutral        | Very Positive |

*Sponsorships generate revenue rather than cost

**Marketing Department Staff** (future expansion):
- **Marketing Director**: Overall strategy, major sponsorships
- **Promotions Manager**: Game-day events, giveaways
- **Sponsorship Coordinator**: Partner relationships
- **Community Relations**: Outreach, charity events

**Integration Points:**
- Depends on Revenue Streams (#32) — Marketing affects revenue
- Depends on Social Media (#13) — Campaigns generate buzz
- Works with Business Dashboards (#31) — Track campaign ROI
- Late-game feature — Built on top of core business systems

---

### Team Statistics (#8)

Comprehensive team-level statistics tracking for offensive, defensive, and special teams performance.

**Core Concepts:**
- **Offensive Stats**: Total yards, passing/rushing yards, first downs, 3rd/4th down efficiency, time of possession
- **Defensive Stats**: Points allowed, yards allowed, sacks, TFLs, INTs, passes defended, defensive TDs
- **Special Teams**: Field goal %, extra point %, punt/kick return yards and TDs
- **Red Zone**: Attempts, touchdowns, field goals, scoring efficiency %
- **Turnovers**: INTs thrown/caught, fumbles lost/recovered, turnover margin

**Team Rankings (1-32):**
| Category | Rankings |
|----------|----------|
| Offensive | Total yards, passing yards, rushing yards, scoring |
| Defensive | Points allowed, yards allowed, turnovers forced |
| Special Teams | FG%, return average |

**Integration Points:**
- Depends on Statistics (#2) — Player stats aggregate to team level
- Feeds into Awards (#10) — Best offense/defense team awards
- Feeds into GM Behaviors (#36) — AI evaluates team strengths
- Affects Business Layer — Fan engagement based on performance

---

### CSV Export (#40)

Export dynasty data to CSV files for external analysis, spreadsheets, or sharing.

**Core Concepts:**
- **Export Types**:
  | Type | Contents |
  |------|----------|
  | Player Stats | Season/career stats by position (passing, rushing, receiving, defense) |
  | Team Stats | Team totals, rankings, standings |
  | Transactions | Signings, trades, cuts, draft picks |
  | Full Roster | All players with contracts, attributes, ratings |

- **UI Access**: Menu bar → Export menu
- **File Format**: CSV with headers, UTF-8 encoding
- **Filters**: By season, team, position

**Integration Points:**
- Depends on Statistics (#2) — StatsAPI provides data
- Uses existing dataclasses for consistent field names

---

### League Settings (#41)

Customize league rules and simulation parameters per dynasty.

**Core Concepts:**
- **Setting Categories**:
  | Category | Settings |
  |----------|----------|
  | Salary Cap | Cap ceiling, floor, rookie pool, minimum salary |
  | Teams | Roster limit, practice squad limit, IR limit |
  | Simulation | Injury frequency, progression rate, AI aggressiveness |

- **UI Access**: Menu bar → Game → Settings
- **Storage**: Per-dynasty settings table in database
- **Validation**: Range checks, type enforcement

**Integration Points:**
- Affects Salary Cap (done) — Custom cap values
- Affects Injuries (#4) — Injury frequency multiplier
- Affects Training Camp (done) — Progression rate multiplier
- Affects GM Behaviors (#37) — AI aggressiveness setting

---

### Owner Communication Portal (#25)

An interactive inbox system where the Owner receives messages, requests, and notifications from all stakeholders. Provides the communication channel for managing the franchise.

**Core Concepts:**
- **Message Sources**:
  | Sender | Examples |
  |--------|----------|
  | GM | Trade proposals, FA recommendations, cap alerts |
  | Coach | Lineup suggestions, injury updates, scheme changes |
  | Players | Contract requests, trade demands, complaints |
  | Media | Interview requests, press inquiries, rumors |
  | Fans | Attendance concerns, pricing feedback |
  | League | Rule changes, fines, schedule updates |

- **Owner Actions**: Approve, Deny, Reply, Defer, Forward, Ignore
- **Message Priority**: Urgent, High, Normal, Low
- **Consequences**: Ignoring urgent messages affects relationships and outcomes

**UI Components:**
- Inbox view with filtering (by sender, priority, status)
- Message detail with action buttons
- Notification badge on main window
- Archive for historical messages

**Integration Points:**
- Foundational for Front Office Direction (#29) — GM proposals come through inbox
- Enables Season Goals (#30) — Progress updates via messages
- Supports Media Coverage (#13) — Media requests route through inbox
- Connects to GM Behaviors (#37) — AI generates contextual messages
- Affects Relationships — Responses impact GM/Coach/Player satisfaction