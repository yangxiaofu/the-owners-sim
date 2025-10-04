# Offseason Event System Architecture

**Version:** 2.0.0
**Last Updated:** 2025-10-04
**Status:** Foundation Complete

## Overview

The Offseason Event System extends the existing event infrastructure to support the complete NFL offseason cycle. All offseason activities are represented as lightweight event classes that integrate with the calendar and simulation executor systems.

### Design Philosophy

1. **Thin Wrappers**: Events define WHEN things happen, not HOW they're processed
2. **Independent Events**: No dependencies between events - each is self-contained
3. **Date-Driven**: Events trigger based on calendar dates via `SimulationExecutor`
4. **Placeholder Logic**: Business logic (salary cap, contracts, AI) added later
5. **BaseEvent Pattern**: All events extend `BaseEvent` with standardized interface

## Event Type Hierarchy

### Foundation Events (Markers)

These events mark important dates but don't execute business logic. They serve as phase markers and informational signals.

#### **DeadlineEvent**
**Purpose:** Marks important NFL offseason deadlines
**Execution:** Returns success immediately with metadata
**Use Cases:**
- Franchise tag deadline (mid-March)
- RFA tender deadline (mid-March)
- Draft declaration deadline (mid-January)
- Salary cap compliance deadline (mid-March)
- June 1 releases deadline
- Rookie contract signing deadline
- Final roster cuts deadline

**Key Properties:**
- `deadline_type`: Type identifier (e.g., "FRANCHISE_TAG", "RFA_TENDER")
- `description`: Human-readable explanation
- `season_year`: NFL season year
- `event_date`: Date when deadline occurs
- `dynasty_id`: Dynasty context for isolation

**Example:**
```python
franchise_deadline = DeadlineEvent(
    deadline_type=DeadlineType.FRANCHISE_TAG,
    description="Deadline to apply franchise or transition tags",
    season_year=2024,
    event_date=Date(2024, 3, 5),
    dynasty_id="my_dynasty"
)
```

---

#### **WindowEvent**
**Purpose:** Marks the start or end of offseason time windows
**Execution:** Logs window opening/closing, updates window state
**Use Cases:**
- Legal Tampering Period (2 days before Free Agency)
- Free Agency Period (March - end of season)
- Draft Preparation Window
- OTA/Minicamp Windows
- Training Camp Period
- Preseason Games Window
- Roster Reduction Phases

**Key Properties:**
- `window_name`: Name of window (e.g., "LEGAL_TAMPERING", "FREE_AGENCY")
- `window_type`: "START" or "END"
- `description`: Human-readable explanation
- `season_year`: NFL season year
- `event_date`: Date when window starts/ends
- `dynasty_id`: Dynasty context

**Example:**
```python
# Free agency begins
fa_start = WindowEvent(
    window_name=WindowName.FREE_AGENCY,
    window_type="START",
    description="Unrestricted free agency period begins",
    season_year=2024,
    event_date=Date(2024, 3, 13),
    dynasty_id="my_dynasty"
)

# Free agency ends
fa_end = WindowEvent(
    window_name=WindowName.FREE_AGENCY,
    window_type="END",
    description="Unrestricted free agency period ends",
    season_year=2024,
    event_date=Date(2024, 7, 22),
    dynasty_id="my_dynasty"
)
```

---

#### **MilestoneEvent**
**Purpose:** Marks informational milestones with no execution logic
**Execution:** Returns metadata only - purely informational
**Use Cases:**
- Super Bowl completion
- Pro Bowl date
- NFL Combine dates (start/end)
- League meetings
- Schedule release
- Hall of Fame induction
- Draft order finalized
- Compensatory picks awarded

**Key Properties:**
- `milestone_type`: Type identifier (e.g., "SUPER_BOWL", "COMBINE_START")
- `description`: Human-readable explanation
- `season_year`: NFL season year
- `event_date`: Date of milestone
- `dynasty_id`: Dynasty context
- `metadata`: Optional additional context (e.g., Super Bowl winner)

**Example:**
```python
super_bowl = MilestoneEvent(
    milestone_type=MilestoneType.SUPER_BOWL,
    description="Super Bowl LIX - Chiefs vs Eagles",
    season_year=2024,
    event_date=Date(2025, 2, 9),
    dynasty_id="my_dynasty",
    metadata={
        "winner_team_id": 12,  # Kansas City Chiefs
        "loser_team_id": 21,   # Philadelphia Eagles
        "final_score": "31-28"
    }
)
```

---

### Action Events (Executable Transactions)

These events represent actual transactions that modify team/player state. Currently return placeholder results; business logic will be added when contract/cap systems are implemented.

---

## Contract Events

Events related to player contracts and salary cap management.

#### **FranchiseTagEvent**
**Purpose:** Apply franchise tag to retain a player for one year
**Business Logic (Future):** Update contract database, adjust salary cap
**NFL Context:**
- Exclusive tag: Player cannot negotiate with other teams
- Non-exclusive tag: Player can negotiate; original team has right to match or receive compensation

**Key Properties:**
- `team_id`: Team applying tag (1-32)
- `player_id`: Player receiving tag
- `tag_type`: "EXCLUSIVE" or "NON_EXCLUSIVE"
- `tag_amount`: Salary (average of top 5 at position)
- `event_date`: Date tag applied
- `dynasty_id`: Dynasty context

**Example:**
```python
tag_event = FranchiseTagEvent(
    team_id=22,  # Detroit Lions
    player_id="player_123",
    tag_type="NON_EXCLUSIVE",
    tag_amount=18_000_000,  # $18M
    event_date=Date(2024, 3, 5),
    dynasty_id="my_dynasty"
)
```

---

#### **TransitionTagEvent**
**Purpose:** Apply transition tag with right of first refusal
**Business Logic (Future):** Update contract database, adjust salary cap
**NFL Context:**
- Player can negotiate with other teams
- Original team can match any offer
- No compensation if team declines to match (unlike franchise tag)

**Key Properties:**
- `team_id`: Team applying tag (1-32)
- `player_id`: Player receiving tag
- `tag_amount`: Salary (average of top 10 at position)
- `event_date`: Date tag applied
- `dynasty_id`: Dynasty context

**Example:**
```python
transition_tag = TransitionTagEvent(
    team_id=22,
    player_id="player_456",
    tag_amount=14_000_000,  # $14M
    event_date=Date(2024, 3, 5),
    dynasty_id="my_dynasty"
)
```

---

#### **PlayerReleaseEvent**
**Purpose:** Release player from contract
**Business Logic (Future):** Update roster, adjust salary cap with dead cap calculations
**NFL Context:**
- Pre-June 1 release: Full cap hit in current year
- Post-June 1 release: Cap hit spread over current + next year

**Key Properties:**
- `team_id`: Team releasing player (1-32)
- `player_id`: Player being released
- `release_type`: "PRE_JUNE_1" or "POST_JUNE_1"
- `cap_savings`: Cap space saved
- `dead_cap`: Dead cap penalty
- `event_date`: Date of release
- `dynasty_id`: Dynasty context

**Example:**
```python
release = PlayerReleaseEvent(
    team_id=22,
    player_id="player_789",
    release_type="POST_JUNE_1",
    cap_savings=8_000_000,   # $8M saved
    dead_cap=4_000_000,      # $4M dead cap
    event_date=Date(2024, 6, 2),
    dynasty_id="my_dynasty"
)
```

---

#### **ContractRestructureEvent**
**Purpose:** Restructure contract to create immediate cap space
**Business Logic (Future):** Update contract terms, recalculate cap hits
**NFL Context:**
- Converts base salary to signing bonus
- Spreads cap hit over remaining contract years
- Creates immediate cap relief but increases future obligations

**Key Properties:**
- `team_id`: Team restructuring (1-32)
- `player_id`: Player whose contract is restructured
- `restructure_amount`: Amount converted to bonus
- `cap_savings_current_year`: Immediate cap space created
- `event_date`: Date of restructure
- `dynasty_id`: Dynasty context

**Example:**
```python
restructure = ContractRestructureEvent(
    team_id=22,
    player_id="player_101",
    restructure_amount=10_000_000,      # $10M converted
    cap_savings_current_year=7_500_000, # $7.5M saved this year
    event_date=Date(2024, 3, 10),
    dynasty_id="my_dynasty"
)
```

---

## Free Agency Events

Events for unrestricted and restricted free agent transactions.

#### **UFASigningEvent**
**Purpose:** Sign unrestricted free agent to new contract
**Business Logic (Future):** Create contract, update roster, adjust salary cap
**NFL Context:**
- Player can sign with any team
- No compensation to former team
- Contract terms negotiated freely

**Key Properties:**
- `team_id`: Team signing player (1-32)
- `player_id`: Player being signed
- `contract_years`: Contract length
- `contract_value`: Total contract value
- `signing_bonus`: Signing bonus amount
- `event_date`: Date of signing
- `dynasty_id`: Dynasty context

**Example:**
```python
ufa_signing = UFASigningEvent(
    team_id=22,
    player_id="player_555",
    contract_years=4,
    contract_value=60_000_000,  # $60M total
    signing_bonus=20_000_000,   # $20M signing bonus
    event_date=Date(2024, 3, 15),
    dynasty_id="my_dynasty"
)
```

---

#### **RFAOfferSheetEvent**
**Purpose:** RFA player receives offer; original team matches or declines
**Business Logic (Future):** Update contract/roster, transfer draft picks if not matched
**NFL Context:**
- Player receives offer from another team
- Original team has 5 days to match
- If declined, signing team gives up draft pick(s) based on tender level

**Key Properties:**
- `original_team_id`: Team with right to match (1-32)
- `signing_team_id`: Team making offer (1-32)
- `player_id`: Player receiving offer
- `offer_amount`: Total offer value
- `contract_years`: Contract length
- `tender_level`: Compensation level ("FIRST_ROUND", "SECOND_ROUND", etc.)
- `matched`: Whether original team matched
- `event_date`: Date of offer/match decision
- `dynasty_id`: Dynasty context

**Example:**
```python
rfa_offer = RFAOfferSheetEvent(
    original_team_id=22,
    signing_team_id=9,
    player_id="player_777",
    offer_amount=12_000_000,  # $12M total
    contract_years=3,
    tender_level="SECOND_ROUND",
    matched=True,  # Lions matched the offer
    event_date=Date(2024, 3, 20),
    dynasty_id="my_dynasty"
)
```

---

#### **CompensatoryPickEvent**
**Purpose:** Award compensatory draft pick for free agency losses
**Business Logic (Future):** Add draft pick to team's draft capital
**NFL Context:**
- Teams losing more/better FAs than they signed receive comp picks
- Picks awarded in rounds 3-7
- Cannot be traded

**Key Properties:**
- `team_id`: Team receiving pick (1-32)
- `pick_round`: Draft round (3-7)
- `pick_number`: Overall pick number
- `reason`: Explanation of what triggered award
- `event_date`: Date pick awarded
- `dynasty_id`: Dynasty context

**Example:**
```python
comp_pick = CompensatoryPickEvent(
    team_id=22,
    pick_round=3,
    pick_number=97,
    reason="Lost QB Matthew Stafford to Team 14 (Rams)",
    event_date=Date(2024, 2, 28),
    dynasty_id="my_dynasty"
)
```

---

## Draft Events

Events for the NFL Draft and post-draft signings.

#### **DraftPickEvent**
**Purpose:** Team selects player in NFL Draft
**Business Logic (Future):** Add player to roster, create rookie contract
**NFL Context:**
- 7 rounds, 32 picks per round (plus compensatory)
- Rookie contracts are slotted based on draft position
- 4-year contracts with 5th year option for 1st rounders

**Key Properties:**
- `team_id`: Team making selection (1-32)
- `round_number`: Draft round (1-7)
- `pick_number`: Overall pick number (1-262+)
- `player_id`: Unique ID for drafted player
- `player_name`: Player's name
- `position`: Player's position
- `college`: Player's college
- `event_date`: Date of selection
- `dynasty_id`: Dynasty context

**Example:**
```python
draft_pick = DraftPickEvent(
    team_id=22,
    round_number=1,
    pick_number=12,
    player_id="draft_2024_12",
    player_name="Jahmyr Gibbs",
    position="RB",
    college="Alabama",
    event_date=Date(2024, 4, 27),
    dynasty_id="my_dynasty"
)
```

---

#### **UDFASigningEvent**
**Purpose:** Sign undrafted free agent after draft
**Business Logic (Future):** Add player to roster, create UDFA contract
**NFL Context:**
- Players not drafted can sign with any team
- Typically receive small signing bonuses
- Compete for roster spots in training camp

**Key Properties:**
- `team_id`: Team signing player (1-32)
- `player_id`: Unique ID for signed player
- `player_name`: Player's name
- `position`: Player's position
- `college`: Player's college
- `signing_bonus`: Signing bonus (typically $5k-$200k)
- `event_date`: Date of signing
- `dynasty_id`: Dynasty context

**Example:**
```python
udfa_signing = UDFASigningEvent(
    team_id=22,
    player_id="udfa_2024_123",
    player_name="John Smith",
    position="WR",
    college="Michigan State",
    signing_bonus=50_000,  # $50k
    event_date=Date(2024, 4, 30),
    dynasty_id="my_dynasty"
)
```

---

#### **DraftTradeEvent**
**Purpose:** Trade draft picks (and optionally players) between teams
**Business Logic (Future):** Transfer picks/players, update draft capital
**NFL Context:**
- Teams can trade current and future picks
- Often package picks with players
- Complex trade value calculations

**Key Properties:**
- `team1_id`: First team (1-32)
- `team2_id`: Second team (1-32)
- `team1_gives_picks`: List of picks team1 trades (round, year, pick_number)
- `team2_gives_picks`: List of picks team2 trades
- `team1_gives_players`: List of player_ids team1 trades (optional)
- `team2_gives_players`: List of player_ids team2 trades (optional)
- `event_date`: Date of trade
- `dynasty_id`: Dynasty context

**Example:**
```python
draft_trade = DraftTradeEvent(
    team1_id=22,  # Lions
    team2_id=9,   # Bears
    team1_gives_picks=[
        {"round": 1, "year": 2024, "pick_number": 12}
    ],
    team2_gives_picks=[
        {"round": 1, "year": 2024, "pick_number": 20},
        {"round": 3, "year": 2024, "pick_number": 84}
    ],
    team1_gives_players=[],
    team2_gives_players=[],
    event_date=Date(2024, 4, 20),
    dynasty_id="my_dynasty"
)
```

---

## Roster Events

Events for roster management, cuts, and player transactions.

#### **RosterCutEvent**
**Purpose:** Cut player to meet roster limits
**Business Logic (Future):** Remove from roster, adjust salary cap, add to waivers
**NFL Context:**
- Teams reduce from 90 to 75 to 53 players
- Final cuts before season starts
- Cut players go through waivers

**Key Properties:**
- `team_id`: Team making cut (1-32)
- `player_id`: Player being cut
- `cut_type`: Type of cut ("TO_75", "TO_53", "INJURY_SETTLEMENT", "MID_SEASON")
- `reason`: Explanation
- `event_date`: Date of cut
- `dynasty_id`: Dynasty context

**Example:**
```python
roster_cut = RosterCutEvent(
    team_id=22,
    player_id="player_999",
    cut_type="TO_53",
    reason="Did not make final roster",
    event_date=Date(2024, 8, 29),
    dynasty_id="my_dynasty"
)
```

---

#### **WaiverClaimEvent**
**Purpose:** Claim player off waivers
**Business Logic (Future):** Add to roster if claim successful, adjust waiver priority
**NFL Context:**
- Cut players go through waivers for 24 hours
- Teams claim based on waiver priority (inverse of standings)
- Highest priority team gets player

**Key Properties:**
- `claiming_team_id`: Team attempting claim (1-32)
- `releasing_team_id`: Team that released player (1-32)
- `player_id`: Player on waivers
- `waiver_priority`: Claiming team's priority (1 = highest)
- `claim_successful`: Whether claim succeeded
- `event_date`: Date of claim
- `dynasty_id`: Dynasty context

**Example:**
```python
waiver_claim = WaiverClaimEvent(
    claiming_team_id=22,
    releasing_team_id=9,
    player_id="player_888",
    waiver_priority=12,
    claim_successful=True,
    event_date=Date(2024, 8, 30),
    dynasty_id="my_dynasty"
)
```

---

#### **PracticeSquadEvent**
**Purpose:** Add/remove/elevate players from practice squad
**Business Logic (Future):** Update practice squad roster, track eligibility
**NFL Context:**
- Up to 16 practice squad players per team
- Players practice but aren't eligible for games
- Can be elevated to active roster for gameday
- Can be protected from other teams

**Key Properties:**
- `team_id`: Team managing practice squad (1-32)
- `player_id`: Player being added/removed/elevated
- `action`: Type of action ("ADD", "REMOVE", "ELEVATE", "PROTECT")
- `reason`: Explanation
- `event_date`: Date of action
- `dynasty_id`: Dynasty context

**Example:**
```python
practice_squad = PracticeSquadEvent(
    team_id=22,
    player_id="player_666",
    action="ELEVATE",
    reason="Elevated for Week 1 game due to injury",
    event_date=Date(2024, 9, 7),
    dynasty_id="my_dynasty"
)
```

---

## Integration with Existing Systems

### Calendar System Integration
All events are stored in the `events` table via `EventDatabaseAPI` and retrieved by date through `SimulationExecutor._get_events_for_date()`.

**Event Triggering Flow:**
1. Calendar advances to new date
2. `SimulationExecutor.simulate_day()` called
3. `_get_events_for_date()` queries database for events on current date
4. Events filtered by dynasty_id for isolation
5. Each event's `simulate()` method executed
6. Results stored via `EventResult`

### Dynasty Isolation
All offseason events include `dynasty_id` parameter to support multiple concurrent dynasty simulations in the same database.

**Dynasty Filtering:**
- Events use dynasty-specific `game_id` format: `{event_type}_{dynasty_id}_{...}`
- `SimulationExecutor` filters events by dynasty context
- Multiple dynasties can coexist without interference

### Event Database Schema
Events stored using existing 3-part structure:
```python
{
    "event_id": str,
    "event_type": str,  # "FRANCHISE_TAG", "UFA_SIGNING", etc.
    "timestamp": datetime,
    "game_id": str,     # Unique identifier with dynasty_id
    "data": {
        "parameters": {...},  # Input values for replay
        "results": None,      # Populated after simulate()
        "metadata": {...}     # Additional context
    }
}
```

---

## Future Enhancements

### Phase 1: Salary Cap System (Future)
When implemented, contract events will:
- Validate cap space before transactions
- Calculate cap hits accurately
- Track dead cap across years
- Handle bonus proration

### Phase 2: AI Decision Engine (Future)
When implemented, events will be generated automatically:
- AI decides which players to tag/release/sign
- Trade evaluation and proposal
- Draft strategy and player selection
- Roster optimization

### Phase 3: Player Evaluation System (Future)
When implemented:
- Scout players before draft
- Evaluate free agents
- Project contract values
- Calculate compensatory pick values

---

## Usage Examples

### Scheduling Offseason Events

```python
from events import (
    DeadlineEvent, WindowEvent, FranchiseTagEvent,
    UFASigningEvent, DraftPickEvent
)
from calendar.date_models import Date

dynasty_id = "lions_rebuild"
season = 2024

# Create franchise tag deadline
tag_deadline = DeadlineEvent(
    deadline_type="FRANCHISE_TAG",
    description="Deadline to apply franchise/transition tags",
    season_year=season,
    event_date=Date(2024, 3, 5),
    dynasty_id=dynasty_id
)

# Create free agency window
fa_start = WindowEvent(
    window_name="FREE_AGENCY",
    window_type="START",
    description="Free agency begins",
    season_year=season,
    event_date=Date(2024, 3, 13),
    dynasty_id=dynasty_id
)

# Store events in database
event_db.insert_event(tag_deadline)
event_db.insert_event(fa_start)

# Events will trigger automatically when calendar reaches their dates
```

### Executing Events via SimulationExecutor

```python
# Calendar advances to March 13, 2024
executor.simulate_day(Date(2024, 3, 13))

# SimulationExecutor retrieves and executes all events for that date:
# - WindowEvent for free agency start
# - Any UFASigningEvent scheduled for that day
# - Any other events on that date

# Events execute polymorphically through BaseEvent.simulate()
```

---

## Event Type Summary

| Event Type | Category | Executes Logic | Purpose |
|------------|----------|----------------|---------|
| DeadlineEvent | Foundation | ❌ No | Mark important deadlines |
| WindowEvent | Foundation | ❌ No | Mark phase transitions |
| MilestoneEvent | Foundation | ❌ No | Informational markers |
| FranchiseTagEvent | Contract | ✅ Future | Apply franchise tag |
| TransitionTagEvent | Contract | ✅ Future | Apply transition tag |
| PlayerReleaseEvent | Contract | ✅ Future | Release player |
| ContractRestructureEvent | Contract | ✅ Future | Restructure contract |
| UFASigningEvent | Free Agency | ✅ Future | Sign UFA player |
| RFAOfferSheetEvent | Free Agency | ✅ Future | RFA offer/match |
| CompensatoryPickEvent | Free Agency | ✅ Future | Award comp pick |
| DraftPickEvent | Draft | ✅ Future | Draft player |
| UDFASigningEvent | Draft | ✅ Future | Sign UDFA |
| DraftTradeEvent | Draft | ✅ Future | Trade picks |
| RosterCutEvent | Roster | ✅ Future | Cut player |
| WaiverClaimEvent | Roster | ✅ Future | Claim player |
| PracticeSquadEvent | Roster | ✅ Future | Manage practice squad |

**Total:** 16 event classes across 5 categories

---

## Version History

**v2.0.0** (2025-10-04)
- Initial implementation of offseason event system
- 16 event classes created as thin wrappers
- Foundation events, contract events, free agency events, draft events, roster events
- Integrated with existing calendar and event infrastructure
- All events return placeholder results (business logic deferred)

---

## Related Documentation

- `docs/plans/offseason_plan.md` - Implementation roadmap
- `docs/specifications/offseason_spec.md` - NFL offseason specification
- `src/events/base_event.py` - Base event interface
- `src/calendar/simulation_executor.py` - Event execution system
