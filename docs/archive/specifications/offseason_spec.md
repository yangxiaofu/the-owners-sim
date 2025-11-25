# NFL Offseason Specification

## Overview

### Purpose
The NFL offseason is the ~7-month period between the Super Bowl (early February) and the start of the regular season (early September). This specification defines all stages, events, and deadlines that occur during this period for simulation purposes.

### Scope
This document covers:
- All official NFL offseason stages and their chronological order
- Key dates, deadlines, and windows
- Contract and roster management events
- Overlapping periods and dependencies
- Implementation considerations for simulation

### Timeline Summary
**Duration**: February - August (7 months)
**Start**: Day after Super Bowl
**End**: Final roster cuts before Week 1

---

## Chronological Timeline

### February (Post-Super Bowl)
| Date | Event | Type |
|------|-------|------|
| Day after Super Bowl | Player releases allowed without 2024 cap impact | Roster Management |
| Feb 17 | Franchise/Transition tag designation period begins | Contract |
| Feb 24 - March 3 | NFL Scouting Combine (Indianapolis) | Evaluation |

### March (Free Agency)
| Date | Event | Type |
|------|-------|------|
| March 4 | Franchise/Transition tag deadline (4:00 PM ET) | Contract |
| March 10 (Noon ET) | Legal tampering period begins | Free Agency |
| March 12 (4:00 PM ET) | New league year begins | League Year |
| March 12 (4:00 PM ET) | Official free agency signing period begins | Free Agency |
| March 12 (4:00 PM ET) | Trading period begins | Transactions |
| March 12 (4:00 PM ET) | Teams must be under salary cap | Salary Cap |
| March 12 (4:00 PM ET) | "Top 51" rule begins (only top 51 salaries count vs cap) | Salary Cap |
| Late March | Annual League Meeting | League Business |

### April (Draft Preparation & Offseason Programs)
| Date | Event | Type |
|------|-------|------|
| April 6 | Offseason workout programs begin (new head coaches) | Training |
| April 20 | Offseason workout programs begin (returning head coaches) | Training |
| April 22 | Deadline for restricted free agent offer sheets | Free Agency |
| April 24-26 | NFL Draft (3 days) | Draft |
| April 26+ | UDFA signing period begins (immediately after draft) | Signings |
| Late April | Compensatory pick deadline for next year's draft | Draft |

### May (Post-Draft & Minicamps)
| Date | Event | Type |
|------|-------|------|
| May 1-2 | 5th-year option deadline (for 2022 1st-round picks) | Contract |
| May 2-12 | Rookie minicamp period (one weekend per team) | Training |
| May 14 | Full regular season schedule release (8:00 PM ET) | Schedule |
| Mid-May - June | OTAs (Phase 3 - 10 days max per team) | Training |
| Late May - June | Mandatory minicamp (1 per team, during Phase 3) | Training |

### June (Offseason Programs Continue)
| Date | Event | Type |
|------|-------|------|
| June 1 | Salary cap accounting date (post-June 1 cuts) | Salary Cap |
| Early-Mid June | OTAs & mandatory minicamps conclude | Training |
| Mid-Late June | Offseason programs end | Training |

### July (Training Camp Begins)
| Date | Event | Type |
|------|-------|------|
| Mid-July | Franchise tag extension deadline (4:00 PM ET) | Contract |
| July 12-16 | Earliest training camp (Hall of Fame teams - rookies) | Training |
| July 16-19 | Earliest training camp (Hall of Fame teams - veterans) | Training |
| July 22 | Typical training camp start (rookies - most teams) | Training |
| July 22 | Typical training camp start (veterans - most teams) | Training |
| Late July | Hall of Fame Game (preseason game 1 for 2 teams) | Preseason |

### August (Preseason & Roster Cuts)
| Date | Event | Type |
|------|-------|------|
| Early August | Preseason Week 1 begins | Preseason |
| Mid-August | Preseason Week 2 | Preseason |
| Late August | Preseason Week 3 | Preseason |
| August 26 (4:00 PM ET) | Final roster cuts (90 to 53) | Roster |
| August 27 (Noon ET) | Waiver claim deadline for cut players | Waivers |
| Late August | Practice squad formation (16 players max) | Roster |

---

## Offseason Stages (Detailed)

### Stage 1: Post-Season Window
**Duration**: February - Early March (3-4 weeks)
**Primary Focus**: Re-signing own players, salary cap management, franchise tags

#### Key Activities:
1. **Own-Team Re-Signing Period**
   - No restrictions on when teams can re-sign their own free agents
   - Teams can negotiate and sign players before free agency
   - Common strategy to lock in key players before market sets prices

2. **Franchise & Transition Tag Period**
   - **Start**: February 17
   - **End**: March 4 (4:00 PM ET)
   - **Franchise Tag**: Prevents player from becoming UFA, guaranteed 1-year contract at position average
   - **Transition Tag**: Right of first refusal, player can negotiate with others
   - **Extension Window**: Tagged players have until mid-July to sign long-term deals

3. **Salary Cap Compliance**
   - **Deadline**: March 12 (4:00 PM ET)
   - Teams must be under salary cap when new league year begins
   - Contract restructures common (convert salary to signing bonus)
   - Player releases/cuts to create cap space
   - Post-February releases don't count against previous year's cap

4. **NFL Scouting Combine**
   - **Duration**: February 24 - March 3 (1 week)
   - **Location**: Indianapolis, Indiana
   - Draft prospect evaluation
   - Medical examinations, interviews, drills

#### Overlaps:
- Re-signing own players can occur throughout entire offseason
- Salary cap work continues until March 12 deadline
- Combine occurs during tag designation period

---

### Stage 2: Free Agency Period
**Duration**: March 10-12 (Legal Tampering) + Ongoing
**Primary Focus**: Acquiring players from other teams

#### Key Phases:

**Phase 2A: Legal Tampering Window**
- **Start**: March 10, Noon ET
- **End**: March 12, 3:59:59 PM ET
- **Duration**: ~52 hours
- **Rules**:
  - Teams contact player **agents only** (not players directly)
  - Deals can be agreed upon but NOT signed
  - No official transactions until new league year
  - Creates market pricing transparency

**Phase 2B: Official Free Agency**
- **Start**: March 12, 4:00 PM ET
- **New League Year Begins**: Same moment
- **Unrestricted Free Agents (UFAs)**:
  - 4+ years experience
  - Contract expired
  - Can sign with any team
- **Restricted Free Agents (RFAs)**:
  - 3 years experience
  - Original team has right of first refusal
  - Tender levels: 1st round, 2nd round, original round, right of first refusal
  - **Offer Sheet Deadline**: April 22

**Phase 2C: Post-Free Agency Exclusive Window**
- **Start**: July 22 (or after)
- **End**: Tuesday after Week 10
- **Rule**: Original team has exclusive negotiating rights to unsigned UFAs

#### Overlaps:
- Trading period begins simultaneously with free agency (March 12)
- Own-team re-signing continues throughout
- "Top 51" rule in effect (only top 51 salaries count vs cap during offseason)

---

### Stage 3: Draft & Post-Draft
**Duration**: Late April - Early May (2 weeks)
**Primary Focus**: Rookie acquisition

#### Key Events:

**NFL Draft**
- **Dates**: April 24-26 (Thursday-Saturday)
- **Rounds**: 7 rounds, 257 total picks (approx.)
- **Compensatory Picks**: 32-35 picks awarded (3rd-7th rounds)
  - Based on previous year's free agency losses
  - **Qualifying Deadline**: April 29 (UFA signings before this date count)
- **Draft Order**: Inverse standings (worst team picks first)

**Post-Draft Signings**
- **Timing**: Immediately after Mr. Irrelevant is selected
- **Undrafted Free Agents (UDFAs)**:
  - 3-year contracts (vs 4 years for drafted rookies)
  - League minimum salary: $840K (2025), $885K (2026), $930K (2027)
  - Signing bonus cap per team (CBA limit)
  - Salary guarantees used to compete for players
  - Bidding war in first few hours post-draft

**Rookie Minicamps**
- **Window**: May 2-12 (either weekend after draft)
- **Duration**: 3 days (Fri-Sun or Sat-Mon)
- **Participants**: Drafted rookies + UDFAs + tryout players
- **Purpose**: First team practices, install basics

**5th-Year Option**
- **Deadline**: May 1-2
- **Applies To**: Players drafted in 1st round of 2022 draft (entering 4th year)
- **Effect**: Team option for 5th year at predetermined salary

#### Overlaps:
- Free agency still active (veteran signings)
- Offseason workout programs running (started April 6/20)
- Draft occurs during Phase 2-3 of workout program

---

### Stage 4: Offseason Workout Program
**Duration**: April - June (9 weeks max)
**Primary Focus**: Conditioning, skill development, team installation

#### Three-Phase Structure:

**Phase 1: Strength & Conditioning**
- **Duration**: 2 weeks
- **Activities**:
  - Meetings (football-related)
  - Strength and conditioning work
  - Physical rehabilitation
  - Film study
- **Restrictions**:
  - NO on-field football activities
  - NO contact with coaches on field
  - Individual workouts only

**Phase 2: Individual & Group Drills**
- **Duration**: 3 weeks
- **Activities**:
  - Individual position drills
  - Group drills (offense vs offense, defense vs defense)
  - 1-on-1, 2-on-2 drills
- **Restrictions**:
  - NO contact permitted
  - NO team drills (11-on-11)
  - NO live action

**Phase 3: OTAs & Minicamp**
- **Duration**: 4 weeks
- **OTA Days**: 10 days maximum per team
- **Activities**:
  - Organized Team Activities (OTAs)
  - 7-on-7, 9-on-7, 11-on-11 drills
  - Team installations (offense/defense/special teams)
  - Mandatory minicamp (1 per team, 3 days)
- **Restrictions**:
  - NO live contact
  - NO pads (helmets only or shorts)
  - Attendance **optional** for OTAs, **mandatory** for minicamp

#### Start Dates by Team Type:
- **New Head Coaches**: April 6
- **Returning Head Coaches**: April 20

#### Overlaps:
- Entire program overlaps with free agency
- Draft occurs during transition from Phase 2 to Phase 3
- Rookie minicamps occur during Phase 3
- Schedule release occurs during OTA period (May 14)

---

### Stage 5: Training Camp & Preseason
**Duration**: July - August (5-6 weeks)
**Primary Focus**: Final roster evaluation, game preparation

#### Training Camp

**Reporting Dates**:
- **Hall of Fame Game Teams** (2 teams):
  - Rookies: ~July 12-16
  - Veterans: ~July 16-19
  - Total: 4 preseason games
- **All Other Teams** (30 teams):
  - Rookies: ~July 22
  - Veterans: ~July 22 (can be 7 days later than rookies max)
  - Total: 3 preseason games

**CBA Rules**:
- Veterans can't report earlier than 15 days before first preseason game
- Rookies can report up to 7 days before veterans
- Specific dates vary by team's preseason schedule

**Training Camp Structure**:
- Full pads allowed
- Live contact permitted
- Team practices (2x per day early, 1x later)
- Installation of full playbook
- Roster evaluation (90 players → 53)

#### Preseason Games

**Hall of Fame Game**:
- **Date**: Late July (~July 31)
- **Teams**: 2 teams (Hall of Fame game participants)
- **Location**: Canton, Ohio

**Regular Preseason Schedule**:
- **Week 1**: Early August (~Aug 7)
- **Week 2**: Mid-August (~Aug 14)
- **Week 3**: Late August (~Aug 21)
- **Total Games**: 3 per team (4 for Hall of Fame teams)

**Game Progression**:
- Week 1: Starters play ~1 quarter
- Week 2: Starters play ~1 half
- Week 3: Starters sit, roster evaluation focus

#### Roster Cuts

**Final Cuts**:
- **Deadline**: August 26, 4:00 PM ET
- **Roster Size**: 90 → 53 players
- **Players Released**: 37 per team (1,184 league-wide)

**Waiver Process**:
- **Waiver Claim Deadline**: August 27, Noon ET
- **Eligible for Waivers**: Players with <4 accrued seasons
- **Waiver Order**: Inverse standings (worst team has priority)
- **Players with 4+ seasons**: Immediate free agents

**Practice Squad Formation**:
- **Size**: 16 players maximum (17 with International Pathway)
- **Eligibility**: Limited NFL experience
- **Timing**: Immediately after cuts
- **Rules**: Can be signed off other teams' practice squads to active roster

#### Overlaps:
- Franchise tag extension deadline (mid-July) during camp
- Free agency technically still active
- Preseason overlaps with final cuts
- Practice squad formation concurrent with regular season prep

---

## Overlapping Periods Analysis

### Concurrent Stages

**1. Own-Team Re-Signing (Continuous)**
- Runs: Entire offseason (Feb - Aug)
- Overlaps: Everything
- No restrictions on timing

**2. February - March Overlap**
```
Feb 17 ─────────────────┐
Franchise Tag Window    │
                        │─── March 4 deadline
                        │
Feb 24 ──────────────────┤
NFL Combine             │
                        │─── March 3
                        │
March 10 ────────────────┤
Legal Tampering         │
                        │─── March 12 (4PM)
March 12 ────────────────┘
Free Agency Begins
League Year Begins
Cap Compliance
```

**3. April - June Overlap**
```
April 6 ─────────────────┐
Workout Phase 1         │
(New HCs)               │
                        │
April 20 ────────────────┤
Workout Phase 1         │
(Returning HCs)         │
                        │
April 24-26 ─────────────┤
NFL Draft               │
                        │
April 26+ ───────────────┤
UDFA Signings           │
                        │
May 2-12 ────────────────┤
Rookie Minicamps        │
                        │
May 14 ──────────────────┤
Schedule Release        │
                        │
May-June ────────────────┤
OTAs (Phase 3)          │
Mandatory Minicamp      │
                        │─── Mid-Late June
                        │
```

**4. July - August Overlap**
```
Mid-July ────────────────┐
Franchise Tag Extension │
Deadline                │
                        │
July 12-22 ──────────────┤
Training Camps Open     │
(staggered by team)     │
                        │
Late July ───────────────┤
Hall of Fame Game       │
                        │
Aug 7-21 ────────────────┤
Preseason Weeks 1-3     │
                        │
Aug 26 ──────────────────┤
Roster Cuts (53)        │
                        │
Aug 27 ──────────────────┤
Waiver Claims           │
Practice Squads         │
                        │─── Early Sept
Regular Season Begins   │
```

### Key Dependency Chains

**Chain 1: Salary Cap → Free Agency → Roster**
```
Restructure Contracts → Cap Compliance (Mar 12) →
  Free Agency → Top 51 Rule → Draft →
    90-Man Roster → Cuts → 53-Man Roster
```

**Chain 2: Draft → Rookies**
```
Draft (Apr 24-26) → UDFA Signings →
  Rookie Minicamp (May 2-12) → OTAs →
    Training Camp (Jul) → Final Roster
```

**Chain 3: Franchise Tag → Extensions**
```
Tag Designation (Feb 17-Mar 4) →
  Negotiation Period (Mar-Jul) →
    Extension Deadline (Mid-Jul) →
      Either: Long-term deal OR Play on tag
```

**Chain 4: Workout Program Progression**
```
Phase 1 (2 weeks) → Phase 2 (3 weeks) →
  Phase 3 (4 weeks + OTAs/Minicamp) →
    Training Camp → Preseason
```

---

## Key Deadlines Reference Table

| Date | Deadline | Impact | Category |
|------|----------|--------|----------|
| Feb 10 | Player releases allowed | No 2024 cap penalty | Roster |
| Feb 17 | Franchise tag window opens | Can designate players | Contract |
| March 4 (4PM) | Franchise/transition tag deadline | Must tag or lose exclusive rights | Contract |
| March 10 (Noon) | Legal tampering begins | Can negotiate with other teams' FAs | Free Agency |
| March 12 (4PM) | Salary cap compliance | Must be under cap | Salary Cap |
| March 12 (4PM) | New league year | Free agency opens, trades allowed | League Year |
| April 6 | Offseason programs (new HCs) | Can begin workouts | Training |
| April 20 | Offseason programs (returning HCs) | Can begin workouts | Training |
| April 22 | RFA offer sheet deadline | Last day to submit offer sheets | Free Agency |
| April 24-26 | NFL Draft | Acquire draft picks | Draft |
| April 29 | Compensatory pick cutoff | UFA signings count toward comp picks | Draft |
| May 1-2 | 5th-year option deadline | Must exercise option for 2022 1st-rounders | Contract |
| May 2-12 | Rookie minicamp window | Can hold 3-day camp | Training |
| May 14 (8PM) | Schedule release | Full season schedule announced | Schedule |
| June 1 | Post-June 1 cut designation | Dead cap split over 2 years | Salary Cap |
| Mid-July (4PM) | Franchise tag extension deadline | Long-term deal or play on tag | Contract |
| July 12-22 | Training camp opens | Rookies/veterans report (staggered) | Training |
| July 22 | Post-FA exclusive window | Original team exclusive rights to UFAs | Free Agency |
| Aug 26 (4PM) | Final roster cuts (90→53) | Must have 53-man roster | Roster |
| Aug 27 (Noon) | Waiver claim deadline | Claim players off waivers | Waivers |
| Early Sept | Regular season begins | Week 1 kickoff | Season Start |

---

## Implementation Considerations

### Event Types Needed

**1. Contract Events**
- `FRANCHISE_TAG_APPLIED` - Player franchised
- `TRANSITION_TAG_APPLIED` - Player transition tagged
- `CONTRACT_RESTRUCTURE` - Salary converted to bonus
- `PLAYER_RE_SIGNED` - Own team re-signing
- `FIFTH_YEAR_OPTION_EXERCISED` - Option picked up

**2. Free Agency Events**
- `LEGAL_TAMPERING_AGREEMENT` - Deal agreed (not signed)
- `UFA_SIGNED` - Unrestricted FA signing
- `RFA_OFFER_SHEET` - Restricted FA offer sheet
- `RFA_MATCHED` - Original team matches
- `RFA_NOT_MATCHED` - Player signs with new team

**3. Draft Events**
- `DRAFT_PICK_MADE` - Team selects player
- `DRAFT_PICK_TRADED` - Pick traded
- `COMPENSATORY_PICKS_AWARDED` - Comp picks assigned
- `UDFA_SIGNED` - Undrafted rookie signed

**4. Roster Events**
- `PLAYER_RELEASED` - Player cut
- `PLAYER_CLAIMED_WAIVERS` - Waiver claim
- `PRACTICE_SQUAD_SIGNED` - Practice squad addition
- `PRACTICE_SQUAD_ELEVATED` - Promoted to active roster

**5. Training Events**
- `OFFSEASON_PROGRAM_START` - Phase 1/2/3 begins
- `OTA_SESSION` - OTA practice day
- `MANDATORY_MINICAMP` - Minicamp attendance
- `ROOKIE_MINICAMP` - Rookie camp
- `TRAINING_CAMP_OPENS` - Camp starts
- `PRESEASON_GAME` - Exhibition game

**6. Administrative Events**
- `NEW_LEAGUE_YEAR` - League year begins (March 12)
- `SALARY_CAP_SET` - Cap announced
- `SCHEDULE_RELEASED` - Season schedule
- `SCOUTING_COMBINE` - Combine week

### Data Structures Required

**Offseason Calendar State**
```python
class OffseasonCalendar:
    current_stage: OffseasonStage  # Which major stage
    current_phase: int  # Phase 1/2/3 for workout program
    league_year: int  # Which NFL year
    salary_cap: int  # Cap amount
    key_dates: Dict[str, Date]  # All deadlines
```

**Player Contract State**
```python
class PlayerContractStatus:
    contract_status: ContractType  # UFA, RFA, Under Contract
    tag_type: Optional[TagType]  # Franchise, Transition, None
    tender_level: Optional[TenderLevel]  # For RFAs
    contract_expiry: Date
    cap_hit: int
    dead_money: int
```

**Team Roster State**
```python
class TeamRosterState:
    active_roster: List[Player]  # 53 during season
    practice_squad: List[Player]  # 16 max
    reserve_lists: Dict[str, List[Player]]  # IR, PUP, etc.
    roster_size: int  # 90 during offseason
    cap_space: int
    pending_fas: List[Player]  # Own players becoming FA
```

**Draft State**
```python
class DraftState:
    current_round: int
    current_pick: int
    draft_order: List[TeamPick]
    compensatory_picks: List[CompPick]
    available_players: List[DraftProspect]
    drafted_players: List[DraftedPlayer]
```

### Simulation Flow

**1. Offseason Progression**
```python
def advance_offseason(days: int):
    for day in range(days):
        # Check for stage transitions
        if should_transition_stage():
            transition_to_next_stage()

        # Process daily events
        process_scheduled_events(current_date)

        # AI team decisions
        for team in teams:
            if needs_decision(team, current_date):
                make_offseason_decision(team)

        # Advance date
        calendar.advance(1)
```

**2. User Interactions**
```python
class OffseasonUI:
    def show_free_agency_board():
        # Display available FAs, salary cap, team needs

    def show_draft_board():
        # Draft prospects, team picks, mock drafts

    def show_roster_management():
        # 90-man roster, cuts needed, cap space

    def show_training_camp():
        # Depth chart, practice performance, injuries
```

**3. AI Decision Making**
```python
def ai_team_offseason_decisions(team, current_stage):
    if current_stage == "POST_SEASON":
        decide_franchise_tags(team)
        resign_own_players(team)

    elif current_stage == "FREE_AGENCY":
        evaluate_free_agents(team)
        make_fa_signings(team)

    elif current_stage == "DRAFT":
        create_draft_board(team)
        make_draft_picks(team)

    elif current_stage == "TRAINING_CAMP":
        evaluate_roster(team)
        make_cuts(team)
```

### UI/UX Considerations

**Offseason Dashboard**
- Current stage indicator
- Days until next major deadline
- Team salary cap status
- Pending decisions (tags, re-signings, cuts)
- Roster status (size, needs)

**Stage-Specific Screens**
- **Free Agency**: Market board, contract offers, cap space
- **Draft**: Draft board, team needs, mock drafts, player scouting
- **Training Camp**: Depth chart, practice reports, roster decisions
- **Roster Management**: 90→53 cuts, practice squad, injury reserves

**Simulation Pacing Options**
- **Day-by-day**: Full control, see all events
- **To next decision**: Auto-sim until user input needed
- **To next stage**: Auto-sim to major milestone
- **Simulate offseason**: AI makes all decisions

### Calendar Integration

**Event Scheduling**
```python
# Offseason events scheduled on calendar
calendar.schedule_event(
    event_type="FRANCHISE_TAG_DEADLINE",
    date=Date(2025, 3, 4),
    time="16:00",
    dynasty_id=dynasty_id
)

calendar.schedule_event(
    event_type="NFL_DRAFT",
    date=Date(2025, 4, 24),
    duration_days=3,
    dynasty_id=dynasty_id
)
```

**Date-Driven Logic**
```python
def get_current_offseason_stage(current_date: Date) -> OffseasonStage:
    if current_date < Date(2025, 3, 12):
        return OffseasonStage.POST_SEASON
    elif current_date < Date(2025, 4, 24):
        return OffseasonStage.FREE_AGENCY
    elif current_date < Date(2025, 5, 15):
        return OffseasonStage.DRAFT_POST_DRAFT
    elif current_date < Date(2025, 7, 1):
        return OffseasonStage.OFFSEASON_PROGRAM
    else:
        return OffseasonStage.TRAINING_CAMP
```

---

## Summary

### Offseason Stage Order (No Gaps)
1. **Post-Season Window** (Feb - Early March)
2. **Free Agency** (March 10-12 + ongoing)
3. **Draft & Post-Draft** (Late April - Early May)
4. **Offseason Workout Program** (April - June)
5. **Training Camp & Preseason** (July - August)

### Major Overlaps
- Own-team re-signing happens throughout entire offseason
- Free agency active during draft and workout programs
- Workout programs start during free agency, continue through draft
- Draft occurs during Phase 2-3 transition
- Some offseason programs overlap with training camp (late teams)

### Critical Deadlines (Absolute)
1. **March 4 (4PM)**: Franchise tag deadline
2. **March 12 (4PM)**: Cap compliance, free agency, new league year
3. **April 22**: RFA offer sheets
4. **May 1-2**: 5th-year options
5. **Mid-July**: Franchise tag extensions
6. **August 26 (4PM)**: Final roster cuts
7. **August 27 (Noon)**: Waiver claims

### Non-Overlapping Deadlines (Firm Sequence)
- Franchise tags → Free agency → Draft → Training camp → Cuts
- Each has distinct decision points and roster implications

### Flexible/Overlapping Windows
- Re-signing own players (anytime)
- Contract restructures (before March 12)
- Offseason program phases (team-dependent start dates)
- Rookie minicamps (choice of 2 weekends)

This specification provides the foundation for implementing a realistic NFL offseason simulation with proper timing, dependencies, and decision points.
