# NFL Free Agency System Specification

**Version:** 1.0
**Last Updated:** October 4, 2025
**Status:** Draft Specification

---

## Table of Contents

1. [Overview & Purpose](#overview--purpose)
2. [Free Agent Types](#free-agent-types)
3. [Timeline & Calendar](#timeline--calendar)
4. [Franchise & Transition Tags](#franchise--transition-tags)
5. [RFA Tender System](#rfa-tender-system)
6. [Contract Structure](#contract-structure)
7. [Salary Cap Rules](#salary-cap-rules)
8. [Compensatory Picks](#compensatory-picks)
9. [Waiver System](#waiver-system)
10. [Negotiation & Market Factors](#negotiation--market-factors)
11. [Implementation Considerations](#implementation-considerations)
12. [Simulation Simplifications](#simulation-simplifications)
13. [Reference Data Tables](#reference-data-tables)

---

## Overview & Purpose

### What is NFL Free Agency?

NFL Free Agency is the system by which players whose contracts have expired can negotiate and sign with new teams. Introduced in its modern form in 1993, it fundamentally changed how NFL teams build their rosters, allowing players to seek the best contract offers from multiple teams while giving teams the opportunity to acquire talent beyond the draft.

### System Goals for The Owners Sim

The free agency system implementation aims to:

1. **Provide Realistic NFL Offseason Experience**: Simulate the actual decision-making and strategic planning NFL teams face during the offseason
2. **Enable Dynasty Mode Depth**: Create long-term roster management challenges and opportunities across multiple seasons
3. **Balance User Control with AI Autonomy**: Allow user teams to actively participate while 31 AI teams operate independently
4. **Integrate with Salary Cap System**: Ensure financial constraints drive realistic team-building decisions
5. **Support Multiple Simulation Speeds**: Allow day-by-day detailed play or quick simulation of entire periods

---

## Free Agent Types

### 1. Unrestricted Free Agents (UFA)

**Definition**: Players with **four or more accrued seasons** whose contracts have expired.

**Characteristics**:
- Free to negotiate and sign with any NFL team
- No draft-choice compensation owed to their previous team
- Can sign anytime after free agency opens (March 12, 4PM ET)
- Signing period extends through July 22 or first day of training camp, whichever is later

**Accrued Season Requirement**:
- A player accrues a season by being on full-play status for at least **6 regular-season games** in a given season
- Practice squad time does NOT count toward accrued seasons
- Players on injured reserve CAN accrue seasons if they were on the roster for 6+ games before injury

**Implementation Notes**:
- Most common type of free agent in the simulation
- Primary market for veteran talent acquisition
- No restrictions on signing except salary cap space

---

### 2. Restricted Free Agents (RFA)

**Definition**: Players with **exactly three accrued seasons** whose contracts have expired.

**Characteristics**:
- Can negotiate with any team, but original team has **Right of First Refusal**
- Original team must extend a "qualifying offer" (tender) to make player an RFA
- If no qualifying offer is extended, player becomes an UFA
- Original team can match any offer sheet signed with another team within 5 days
- Depending on tender level, acquiring team may owe draft pick compensation

**Special Rules**:
- Player cannot sign offer sheet until after April 22 deadline (2025)
- If original team matches, player must return to original team on matched terms
- If original team declines to match, they receive draft pick compensation (if applicable)
- Players can only be RFAs once in their career (after 3rd accrued season)

**Implementation Notes**:
- Requires offer sheet system (team makes offer, original team responds)
- Must track tender levels and associated compensation
- 5-day matching window must be simulated
- Affects draft pick allocation for compensatory picks

---

### 3. Exclusive Rights Free Agents (ERFA)

**Definition**: Players with **fewer than three accrued seasons** whose contracts have expired.

**Characteristics**:
- Original team has **exclusive negotiating rights**
- Cannot negotiate with other teams at all
- Must accept team's one-year minimum salary tender or sit out
- Most limited form of free agency

**Tender Requirements**:
- Team must offer **one-year contract at minimum salary** for player's experience level
- If team doesn't offer tender, player becomes UFA (rare)
- No draft pick compensation ever applies

**Implementation Notes**:
- Simplest free agent type - essentially automatic re-signing
- Rarely contested by players
- AI teams should automatically tender all ERFA players they want to keep

---

### 4. Vested Veterans

**Definition**: Players with **four or more accrued seasons** (same as UFA, but special waiver rules apply).

**Special Waiver Rules**:
- **Before Trade Deadline** (Nov 5): Released vested veterans do NOT go through waivers - they become immediate free agents
- **After Trade Deadline** (Nov 5+): Released vested veterans MUST clear waivers before becoming free agents

**Why This Matters**:
- Teams can release high-salary veterans mid-season and make them immediately available as free agents
- After trade deadline, prevents teams from strategically releasing players to specific teams
- Creates different dynamics for in-season vs. offseason roster moves

**Implementation Notes**:
- Track trade deadline date (November 5)
- Apply different waiver rules based on release date
- Important for in-season roster management simulation

---

## Timeline & Calendar

### Complete Free Agency Calendar (2025 Reference)

| Date | Event | Description |
|------|-------|-------------|
| **February 9** | Super Bowl LIX | End of 2024 season |
| **February 17** | Franchise Tag Window Opens | Teams can begin applying tags |
| **February 24 - March 3** | NFL Scouting Combine | Player evaluation period |
| **Late February** | Salary Cap Announcement | League announces next year's cap |
| **March 4, 4PM ET** | **Franchise Tag Deadline** | Last day to apply franchise/transition tags |
| **March 10, 12PM ET** | **Legal Tampering Begins** | Teams can negotiate (but not sign) with UFAs |
| **March 12, 4PM ET** | **New League Year Begins** | Free agency opens, contracts can be signed |
| **March 12, 4PM ET** | Trading Period Opens | Teams can trade players and picks |
| **March 23-26** | Annual League Meeting | Owners discuss rule changes |
| **April 22** | **RFA Offer Sheet Deadline** | Last day for RFA offer sheets |
| **April 24-26** | **NFL Draft** | 7 rounds over 3 days (Green Bay 2025) |
| **May 2** | **5th-Year Option Deadline** | Deadline to exercise 5th-year options on 2022 first-round picks |
| **May 14, 8PM ET** | Schedule Release | Full regular season schedule announced |
| **May - June** | OTAs (Organized Team Activities) | Voluntary offseason practices |
| **June** | Mandatory Minicamp | 3-day mandatory practice period |
| **Mid-July** | Franchise Tag Extension Deadline | Tagged players must sign long-term deal or play on tag |
| **July 16+** | Training Camps Open | Teams convene full rosters |
| **August** | Preseason Games | 3 preseason games per team |
| **August 26, 4PM ET** | **Final Roster Cuts** | Rosters must be reduced to 53 players |
| **August 27, 12PM ET** | **Waiver Claim Deadline** | Claims on cut players processed |
| **September 4** | Regular Season Begins | Week 1 kickoff |

### Key Windows & Periods

**1. Franchise Tag Window** (Feb 17 - March 4)
- 16-day period for teams to apply tags
- Strategic timing: tag early to prevent negotiation, or late to see market develop
- One franchise tag and one transition tag maximum per team

**2. Legal Tampering Period** (March 10, 12PM - March 12, 4PM)
- 52-hour window where teams can negotiate with UFAs but not finalize contracts
- Allows deals to be "agreed in principle" for immediate signing when free agency opens
- Violations can result in fines and loss of draft picks

**3. Free Agency Signing Period** (March 12, 4PM onwards)
- Official start of new league year
- Contracts can be officially signed and filed with league
- Continues through July 22 or training camp start

**4. RFA Negotiation Window** (March 12 - April 22)
- RFAs can receive offer sheets from other teams
- Original team has 5 days to match after offer sheet signed
- Most RFA movement happens early in this window

**5. Post-Draft UDFA Period** (April 26+ for ~72 hours)
- Undrafted free agents can be signed immediately after draft
- Intense 2-3 day signing period for rookie free agents
- Teams limited to signing ~20 UDFAs to 90-man roster

**6. Training Camp Period** (July 16 - August 26)
- 90-man rosters throughout camp
- Final evaluations before roster cuts
- Last opportunity to trade for/sign veterans

---

## Franchise & Transition Tags

### Purpose & Strategy

Teams use tags to retain key players whose contracts have expired while buying time to negotiate long-term deals. Tags are one-year contracts at guaranteed salaries based on positional market averages.

### Tag Types Comparison

| Feature | Non-Exclusive Franchise | Exclusive Franchise | Transition |
|---------|-------------------------|---------------------|------------|
| **Salary Calculation** | Top 5 position avg (last 5 years) OR 120% previous salary | Top 5 position avg (current year) OR 120% previous salary | Top 10 position avg (last 5 years) |
| **Can Negotiate with Others?** | Yes | No | Yes |
| **Original Team Rights** | Right to match + 2 first-round picks if no match | N/A (exclusive) | Right to match only |
| **Compensation if No Match** | Two 1st-round picks | N/A | None |
| **Typical Salary** | Lower (uses 5-year average) | Higher (uses current year) | Lowest (Top 10 vs Top 5) |
| **Strategic Use** | Most common - allows player freedom but keeps compensation | Prevent negotiation entirely | Rarely used - weak leverage |

### 2025 Example Tag Salaries (by Position)

| Position | Non-Exclusive Franchise Tag | Exclusive Franchise Tag | Transition Tag |
|----------|----------------------------|-------------------------|----------------|
| QB | ~$31.8M | ~$33.5M | ~$28.5M |
| RB | ~$12.1M | ~$13.0M | ~$10.5M |
| WR | ~$21.8M | ~$22.5M | ~$19.2M |
| TE | ~$14.2M | ~$15.1M | ~$12.8M |
| OT | ~$20.5M | ~$21.3M | ~$18.7M |
| DE/EDGE | ~$19.8M | ~$20.6M | ~$17.9M |
| DT | ~$18.3M | ~$19.1M | ~$16.5M |
| LB | ~$16.7M | ~$17.5M | ~$15.0M |
| CB | ~$19.0M | ~$19.8M | ~$17.2M |
| S | ~$14.8M | ~$15.5M | ~$13.4M |
| K | ~$5.4M | ~$5.7M | ~$4.8M |
| P | ~$4.9M | ~$5.2M | ~$4.4M |

*Note: These are approximate 2025 values and fluctuate based on new contracts signed*

### Tag Mechanics & Rules

**Applying the Tag**:
1. Team must designate player between Feb 17 - March 4
2. Tag counts immediately against salary cap
3. Player cannot negotiate with other teams (exclusive) or can negotiate but team has rights (non-exclusive)
4. Player must be notified in writing

**Player Response Options**:
1. **Sign the Tag**: Accept one-year deal at tag salary
2. **Refuse to Sign**: Hold out (rare, risky - can be fined, lose accrued season)
3. **Negotiate Long-Term**: Continue negotiating extension with team
4. **Sign Offer Sheet** (non-exclusive only): Force original team to match or lose player + picks

**Long-Term Extension Deadline**:
- **Mid-July** (approximately July 15): Deadline for tagged player to sign multi-year extension
- After deadline, player MUST play on one-year tag tender (cannot extend until after season)
- This prevents year-long negotiation uncertainty

**Consecutive Tag Rules**:
- **First Tag**: Calculated normally (top 5 or top 10 average)
- **Second Consecutive Tag** (same player, next year): 120% of previous tag salary OR normal calculation, whichever is HIGHER
- **Third Consecutive Tag**: 144% of previous tag salary (44% increase)
- **Practical Limit**: Very rare to tag player 3+ times due to cost escalation

### Strategic Considerations

**When to Use Non-Exclusive Franchise Tag**:
- Player is elite but negotiations stalled
- Want to keep player but willing to accept 2 first-round picks if someone overpays
- Most common tag usage (~90% of franchise tags)

**When to Use Exclusive Franchise Tag**:
- Must absolutely keep player and prevent negotiation
- Player is so valuable that 2 first-round picks isn't enough compensation
- Willing to pay premium salary to prevent market test

**When to Use Transition Tag**:
- Rarely used due to weak leverage (no compensation if player leaves)
- Useful for: "We want you, but not at any price" situations
- Player likely stays because other teams won't overpay without compensation to original team

**When NOT to Tag**:
- Player demands trade if tagged (creates bad situation)
- Team has no cap space for tag salary
- Player's market value is significantly lower than tag amount
- Already tagged player twice (third tag too expensive)

---

## RFA Tender System

### Tender Levels & Costs (2025)

Restricted free agents can receive four different tender levels from their original team:

| Tender Level | 2025 Salary | Draft Pick Compensation | Right of First Refusal |
|--------------|-------------|-------------------------|------------------------|
| **First-Round Tender** | $7,458,000 | Original 1st-round pick | Yes |
| **Second-Round Tender** | $5,346,000 | Original 2nd-round pick | Yes |
| **Original-Round Tender** | $3,406,000 | Pick from round player was drafted | Yes |
| **Right of First Refusal Only** | $3,263,000 | None | Yes |

**Important**: All tender amounts are "OR 110% of player's previous year salary, whichever is GREATER"

### How RFA Process Works

**Step 1: Team Extends Qualifying Offer** (by March 12)
- Team must decide which tender level to offer
- Tender becomes guaranteed one-year contract offer
- Player becomes RFA (vs. UFA if no tender offered)

**Step 2: Player Shops Market** (March 12 - April 22)
- Can negotiate with any team
- Other teams can make offers but cannot sign player yet
- Teams evaluate if compensation cost is worth player

**Step 3: Team Makes Offer Sheet** (by April 22)
- Interested team submits formal offer sheet with contract terms
- Offer sheet includes salary, years, guarantees, bonuses
- Must be willing to surrender draft pick(s) based on tender level

**Step 4: Original Team Responds** (5 days to match)
- Has exactly 5 days to match offer sheet terms
- If matched: Player MUST return to original team on those exact terms
- If declined: Player goes to new team, original team receives draft pick(s)

**Step 5: Contract Finalized**
- If matched: Player signs with original team
- If not matched: Player signs with new team, draft picks transfer

### Strategic Tender Selection

**First-Round Tender ($7.458M)**:
- **Use When**: Elite talent you absolutely want to keep
- **Effect**: Very few teams willing to surrender 1st-round pick
- **Risk**: Expensive if player underperforms on one-year deal

**Second-Round Tender ($5.346M)**:
- **Use When**: Strong starter but not elite, moderate interest expected
- **Effect**: Some teams willing to give up 2nd-rounder for quality starter
- **Risk**: Balanced - adequate compensation if lost

**Original-Round Tender ($3.406M)**:
- **Use When**: Mid-round pick showing promise, want to retain cheaply
- **Effect**: Compensation matches original investment
- **Risk**: If player was 6th-7th round pick, minimal deterrent
- **Note**: Undrafted players get no compensation (essentially right of first refusal only)

**Right of First Refusal Only ($3.263M)**:
- **Use When**: Marginal player, willing to match only if offer is reasonable
- **Effect**: No compensation if lost, but keeps player at minimum cost
- **Risk**: Player can leave for better opportunity with no return

### Tender Level Examples

**Scenario 1: 2nd Round Pick, Breakout Season**
- Player drafted in 2nd round (2022), breakout 3rd year (2024)
- Team options:
  - 1st-round tender ($7.458M) → Likely keeps player, may be overpay
  - 2nd-round tender ($5.346M) → Fair value, some risk of offer sheet
  - Original tender ($3.406M) → High risk, only 2nd-round compensation if lost
- **Recommendation**: 2nd-round tender for balanced cost/retention

**Scenario 2: 6th Round Pick, Solid Contributor**
- Player drafted in 6th round (2022), solid but not spectacular
- Team options:
  - 2nd-round tender ($5.346M) → Overpay, but strong retention
  - Original tender ($3.406M) → Reasonable, but 6th-round compensation weak
  - Right of first refusal ($3.263M) → Cheapest, can match if needed
- **Recommendation**: Right of first refusal to save cap, willing to match reasonable offers

**Scenario 3: Undrafted, Pro Bowl Performance**
- Player signed as UDFA (2022), made Pro Bowl in 3rd year
- Team options:
  - 1st-round tender ($7.458M) → Strong retention, high cost
  - 2nd-round tender ($5.346M) → Moderate retention, fair cost
  - Original/Right of first refusal ($3.406M/$3.263M) → High risk, NO compensation (undrafted)
- **Recommendation**: 1st or 2nd-round tender despite undrafted status

---

## Contract Structure

### Contract Components

NFL contracts are complex financial instruments with multiple components that affect both the team's salary cap and the player's actual compensation.

#### 1. Signing Bonus

**Definition**: Lump sum payment made when contract is signed

**Key Characteristics**:
- **Paid Immediately**: Full amount typically paid within first 12-18 months
- **Prorated**: Cap hit spread evenly over contract length (max 5 years)
- **Fully Guaranteed**: Cannot be taken back once paid
- **Acceleration**: If player cut, remaining prorated amounts "accelerate" to current year (dead money)

**Example**:
```
5-year, $50M contract with $15M signing bonus

Year 1: $3M signing bonus cap hit (+ base salary)
Year 2: $3M signing bonus cap hit (+ base salary)
Year 3: $3M signing bonus cap hit (+ base salary)
Year 4: $3M signing bonus cap hit (+ base salary)
Year 5: $3M signing bonus cap hit (+ base salary)

If cut after Year 2:
- $9M in remaining bonus ($3M x 3 years) accelerates to Year 3 cap = "Dead Money"
```

**Strategic Use**:
- Team: Spreads cap hit over multiple years, creates cap flexibility early
- Player: Guaranteed money received upfront, protected against injury/release

---

#### 2. Base Salary

**Definition**: Annual salary paid during the season (typically 17 equal paychecks)

**Key Characteristics**:
- **Paid During Season**: One paycheck per week for 17 weeks + training camp
- **Can Be Guaranteed**: May be fully guaranteed, partially guaranteed, or not guaranteed
- **Cap Hit Year-by-Year**: Full amount counts against cap in year earned
- **Restructure Target**: Can be converted to signing bonus to create cap space

**Guarantee Types for Base Salary**:
- **Fully Guaranteed**: Protected for injury, skill, and cap (all three) - player gets paid no matter what
- **Injury Guaranteed**: Player gets paid if injured, but not if cut for performance/cap
- **Not Guaranteed**: Team can cut player and owe nothing

**Example**:
```
3-year contract:
Year 1: $5M base (fully guaranteed)
Year 2: $8M base (injury guaranteed only)
Year 3: $10M base (not guaranteed)

If player injured in Year 2: Gets Year 2 salary ($8M)
If player cut for performance in Year 2: Gets nothing (not skill guaranteed)
If player cut after Year 2: Year 3 salary ($10M) not owed
```

---

#### 3. Roster Bonus

**Definition**: Bonus paid if player is on roster on specific date

**Key Characteristics**:
- **Date-Specific**: Paid if on roster on March 15, April 1, etc.
- **Counts in Full**: Full amount counts against cap in year earned (unless guaranteed at signing)
- **Guarantee Mechanism**: Can be guaranteed at signing (then prorated like signing bonus)
- **Retention Tool**: Incentivizes team to keep player through specific date

**Strategic Use**:
- Often used in March to guarantee money before free agency starts
- Creates decision points: "Keep player and pay bonus, or cut before date?"

**Example**:
```
Contract with $2M roster bonus due March 15

Team Options Before March 15:
1. Keep player → Pay $2M bonus, counts against cap
2. Cut player → Save $2M, but lose player

This creates natural "evaluation deadline" for team
```

---

#### 4. Workout Bonus

**Definition**: Bonus for attending voluntary offseason workouts

**Key Characteristics**:
- **Attendance Based**: Typically 80-90% attendance required
- **Modest Amounts**: Usually $100K-$500K
- **Not Guaranteed**: Player must actually attend to earn
- **Cap Flexibility**: Doesn't count until earned

**Strategic Use**:
- Encourages veteran attendance at voluntary workouts
- Adds to player compensation without major cap commitment

---

#### 5. Performance Bonuses

**Definition**: Bonuses earned for achieving statistical or playing time milestones

**Types**:
- **Per-Game Roster Bonuses**: Paid for each game on active roster ($100K per game common)
- **Playing Time Bonuses**: Based on snap count percentage (50% snaps = $500K, etc.)
- **Statistical Bonuses**: Yards, TDs, sacks, interceptions, etc.
- **Pro Bowl/All-Pro Bonuses**: Additional money for postseason honors

**Cap Treatment**:
- **Not Likely To Be Earned (NLTBE)**: Doesn't count until earned, then counts next year
- **Likely To Be Earned (LTBE)**: Counts against cap immediately, credited back if not earned

**LTBE vs NLTBE Determination**:
- **LTBE**: Player achieved milestone previous year → assume will achieve again
- **NLTBE**: Player did NOT achieve milestone previous year → assume won't achieve

**Example**:
```
WR with 1,200 receiving yards in 2024

2025 Contract Bonuses:
- 1,000+ yards = $500K (LTBE - counts immediately, he did it in 2024)
- 1,500+ yards = $500K (NLTBE - doesn't count, he didn't hit in 2024)

If he gets 1,600 yards in 2025:
- Both bonuses paid ($1M total)
- NLTBE $500K counts against 2026 cap (unexpected achievement)
```

---

#### 6. Option Bonuses

**Definition**: Bonuses paid when team exercises contract option (future years)

**Key Characteristics**:
- **Prorated Like Signing Bonus**: Spread over remaining years (max 5)
- **Trigger Date**: Usually in offseason of option year
- **Not Guaranteed Initially**: Only paid if option exercised
- **Cap Management Tool**: Creates future cap flexibility

**Example**:
```
5-year contract with Year 4 option:

Year 3 (March 1): Team must decide to exercise Year 4 option
- If exercised: $6M option bonus paid, prorated $3M/year (Year 4-5)
- If declined: Player becomes free agent, no bonus paid
```

---

### Guaranteed Money Structure

**Three Guarantee Protections**:

1. **Skill Guarantee**: Protected if cut for lack of skill/performance
2. **Injury Guarantee**: Protected if injured and unable to play
3. **Cap Guarantee**: Protected if cut for salary cap reasons

**Fully Guaranteed = All Three Protections**

**Guarantee Timing**:
- **Guaranteed at Signing**: Money is locked in day 1 (most secure for player)
- **Guaranteed on Date**: Money becomes guaranteed on future date (March 15, 2026, etc.)
- **Guaranteed for Injury Only**: Becomes fully guaranteed if injured before date

**Example Contract Structure**:
```
5-year, $100M contract ($20M/year average)

Year 1: $15M base (fully guaranteed at signing) + $20M signing bonus
Year 2: $18M base (fully guaranteed at signing)
Year 3: $20M base (becomes guaranteed March 15, 2027)
Year 4: $22M base (injury guarantee only)
Year 5: $25M base (not guaranteed)

Total Guaranteed at Signing: $53M ($15M + $18M + $20M signing bonus)
Additional Guarantees if Kept: $20M (Year 3) + $22M if injured (Year 4)
Maximum Guarantees: $95M
```

---

### Dead Money & Accelerated Cap Hits

**Dead Money Definition**: Salary already paid or committed but not yet charged to cap

**When Dead Money Occurs**:
- Player is released/traded before contract ends
- Remaining prorated signing bonus accelerates to current year
- Any guaranteed base salaries still owed

**Calculation Formula**:
```
Dead Money = Remaining Prorated Signing Bonus + Guaranteed Salaries Not Yet Paid
```

**Example**:
```
5-year, $50M contract:
- $15M signing bonus (prorated $3M/year)
- Year 1-2: $8M base (guaranteed)
- Year 3-5: $7M base (not guaranteed)

Player cut after Year 2:

Dead Money = ($3M x 3 remaining years signing bonus) + $0 future guaranteed salary
          = $9M dead cap hit in Year 3

Team Savings = Avoided Year 3-5 base salaries ($21M) - Dead Money ($9M)
             = $12M net cap savings
```

**June 1 Designation**:
- Special rule allowing dead money to be split across 2 years
- If player cut after June 1 OR designated as "June 1 cut":
  - Current year: Only that year's prorated bonus counts
  - Next year: Remaining prorated bonus counts
- Teams get 2 "June 1 designations" per year (can cut before June 1 but apply rule)

**June 1 Example**:
```
Same contract, cut after Year 2 with June 1 designation:

Year 3 Dead Money = $3M (only Year 3 proration)
Year 4 Dead Money = $6M ($3M x 2 remaining years)

Instead of $9M hit in Year 3, spread as $3M + $6M
```

---

### Contract Restructures

**Purpose**: Create immediate cap space by converting base salary to signing bonus

**Mechanic**:
1. Take current or future year base salary
2. Convert to signing bonus paid immediately
3. Prorate signing bonus over remaining contract years
4. Immediate cap relief, but "pushes money into future"

**Example**:
```
Player has $12M Year 3 base salary, 3 years remaining

Before Restructure:
Year 3 cap hit: $12M
Year 4 cap hit: $8M
Year 5 cap hit: $8M

Team Restructures Year 3 Salary:
- $12M base → $12M signing bonus (paid immediately to player)
- Prorated over 3 years = $4M/year

After Restructure:
Year 3 cap hit: $4M (save $8M this year!)
Year 4 cap hit: $8M + $4M = $12M
Year 5 cap hit: $8M + $4M = $12M

Net Effect: $8M cap savings in Year 3, but $4M added to Year 4-5
```

**Strategic Considerations**:
- **Pros**: Immediate cap relief, player gets guaranteed money now
- **Cons**: Less flexibility in future, more dead money if player cut
- **"Kicking the can"**: Common phrase for pushing cap problems to future

---

### Rookie Contracts (Draft Picks)

**Slotted System**: Each draft pick has predetermined contract value

**Structure**:
- **All 4-Year Deals**: Every draft pick gets 4-year contract
- **5th-Year Option**: Only 1st-round picks have team option for 5th year
- **Fully Slotted**: Salary determined by draft position, minimal negotiation

**5th-Year Option Rules**:
- Must be exercised by **May 2** of player's 4th season (2025: for 2022 1st-rounders)
- Fully guaranteed for injury at exercise
- Becomes fully guaranteed on first day of 5th-year league year
- Salary based on position and performance:
  - **Pro Bowl x2**: Top 10 average at position
  - **Pro Bowl x1**: Top 20 average at position
  - **No Pro Bowl**: Transition tag value

**Example**:
```
2022 1st-round WR (Pick #15)

Years 1-4: Slotted contract ~$14M total
Year 4 (May 2, 2025): Team exercises 5th-year option
Year 5 (2026): $10.9M (Pro Bowl x1 = Top 20 WR average)
```

---

## Salary Cap Rules

### Salary Cap Overview

**Definition**: Maximum amount each team can spend on player salaries in a given season

**2025 Salary Cap**: Approximately **$255 million** per team (projected)

**Purpose**:
- Competitive balance - prevents rich teams from buying championships
- Cost certainty - controls league-wide player costs
- Parity - "any given Sunday" philosophy

---

### Cap Calculation & Components

**What Counts Against Cap**:
- Base salaries
- Prorated signing bonuses
- Roster bonuses (if earned)
- Workout bonuses (if earned)
- Likely To Be Earned performance bonuses
- Option bonuses (prorated)

**What Does NOT Count**:
- Not Likely To Be Earned bonuses (until next year if earned)
- Practice squad salaries
- Injured reserve salaries (count, but team gets relief)
- Benefits and 401(k) contributions

**Top 51 Rule** (Offseason):
- During offseason, only **top 51 cap hits** count toward cap
- Allows teams to have 90-man rosters without all counting
- Once season starts, all 53 players count

---

### Minimum Salaries (2025 Season)

Players must be paid at least minimum salary based on **credited seasons** (similar to accrued, but includes practice squad time).

| Credited Seasons | 2025 Minimum Salary |
|------------------|---------------------|
| 0 (Rookie) | $795,000 |
| 1 | $915,000 |
| 2 | $1,005,000 |
| 3 | $1,080,000 |
| 4-6 | $1,165,000 |
| 7-9 | $1,250,000 |
| 10+ | $1,365,000 |

**Veteran Salary Benefit**:
- Veterans (4+ seasons) can be signed at veteran minimum
- Cap charge is only **2nd-year minimum** ($915,000)
- Team pays veteran full minimum ($1,165,000+), league pays difference
- Encourages teams to sign veteran depth without cap penalty

**Example**:
```
Team signs 10-year veteran to minimum contract

Player Receives: $1,365,000 (10+ year minimum)
Team Cap Hit: $915,000 (2nd-year minimum)
League Pays: $450,000 difference
```

---

### Practice Squad Rules (2025)

**Size**: 16 players per team (17 if International Pathway Program player included)

**Eligibility**:
- **10 players maximum** with 2 or fewer accrued seasons
- **6 players maximum** with unlimited accrued seasons (veteran flexibility)

**Salaries**:
- **Players with <2 seasons**: $13,000/week ($234,000 for full 18-week season)
- **Players with 2+ seasons**: $17,500/week minimum, $22,000/week maximum
- **Note**: Practice squad salaries do NOT count against salary cap

**Practice Squad Rules**:
- Players can be signed off other teams' practice squads to active rosters at any time
- Original team can protect 4 practice squad players per week (cannot be signed away)
- Players can be elevated to active roster for gameday (max 3 times per season)

**Strategic Use**:
- Developmental players
- Injury replacements
- Scheme-specific players (simulate opponent)
- Veterans willing to stay with team at low cost

---

### Salary Cap Compliance

**Deadline**: **March 12, 4PM ET** (when new league year begins)

**Required**: All 32 teams MUST be under salary cap by this deadline

**If Over Cap**:
- **Cannot sign free agents**
- **Cannot make trades** (except to shed salary)
- **Forced cuts/restructures** until compliant
- **League intervention** if team refuses to comply (commissioner can void contracts)

**Common Compliance Methods**:

1. **Release Players**
   - Cut high-salary, low-production veterans
   - Incur dead money but save net cap space
   - Usually Post-June 1 designations to spread dead money

2. **Restructure Contracts**
   - Convert base salary to signing bonus
   - Immediate cap relief, future cap hits
   - Requires player cooperation (but player gets guaranteed money early)

3. **Trade Players**
   - Trade high-salary players for picks/cheaper players
   - Salary cap hit leaves with player (except dead money)
   - Both teams must be under cap after trade

4. **Extension/Pay Cut Negotiations**
   - Negotiate lower salary with player (rare)
   - Extend contract with lower near-term cap hits
   - Requires player willingness

---

### Salary Cap Penalties

**Circumvention Violations**:
- **Illegal side agreements**: Secret payments outside contract
- **Deferred payments**: Trying to hide money from cap
- **Undisclosed bonuses**: Not reporting payments to league

**Penalties**:
- Loss of draft picks (can be multiple years)
- Heavy fines ($5M+ to team, $500K+ to individuals)
- Contract voiding
- Suspension of team executives

**Historical Examples**:
- 2012 Cowboys & Redskins: $10M and $36M cap penalties for front-loading contracts in uncapped 2010
- 2007 49ers: Lost 5th-round pick for salary cap violation

---

### Salary Cap Floor

**Requirement**: Teams must spend minimum percentage of cap over rolling period

**Current Rules**:
- **89% of cap minimum** over any 4-year period
- **95% of cap minimum** league-wide (all 32 teams combined)

**Purpose**: Prevents cheap owners from pocketing revenue-sharing money instead of spending on talent

**Penalty**: Must pay shortfall directly to players on roster at end of period

**Example**:
```
4-year period (2022-2025) with $240M avg cap:

Required Spending: 89% x ($240M x 4 years) = $854M over 4 years

If Team Only Spent: $800M
Shortfall: $54M
Penalty: $54M split among players on 2025 roster as bonus
```

---

## Compensatory Picks

### Purpose & Philosophy

**Compensatory Draft Picks** are awarded to teams that lose more or better free agents than they acquire, rewarding teams that develop talent and lose players to free agency while discouraging "buying" free agents.

### Eligibility Requirements

**Team Eligibility**:
- Team must have **net loss** of Compensatory Free Agents (CFAs)
- Lost more or better CFAs than gained
- OR lost same number but higher value CFAs

**Player Eligibility (Compensatory Free Agent)**:
A player MUST meet ALL of these to be a CFA:

1. **Contract Expired Naturally**
   - NOT released/cut (most important rule)
   - NOT unsigned restricted free agent
   - Contract simply ran out

2. **Signed with Different Team**
   - Cannot count if player retired
   - Cannot count if player unsigned

3. **Top 35 Salary Rank**
   - Among all free agents signed that year
   - Helps filter out minimum salary signings

**What Disqualifies Players**:
- ❌ Released/cut by team (most common)
- ❌ Unsigned restricted free agents (no tender accepted)
- ❌ Traded players
- ❌ Retired players
- ❌ Players who don't sign anywhere

---

### Compensatory Formula

**Formula Inputs** (NFL proprietary, but known factors):

1. **Average Per Year (APY)**: Contract's annual salary
   - **Inverse ranking**: Highest APY gets most points
   - Most heavily weighted factor

2. **Snap Count Percentage**: Offensive or defensive snaps played
   - Must play **minimum 25% of snaps** to qualify
   - Each percentage point = 1 point in formula
   - Only counts snaps for NEW team

3. **Postseason Honors**:
   - Pro Bowl selection
   - All-Pro team
   - Awards additional points

**Final Numerical Value**:
- Sum of points from all three factors
- Higher FNV = Higher draft pick compensation
- Used to determine round (3rd-7th)

**Example Calculation** (simplified):
```
WR signed to 4-year, $60M contract ($15M/year)

APY Ranking: 5th-highest WR signing → 150 points
Snap Count: Played 85% of snaps → 85 points
Pro Bowl: Selected → 50 bonus points

Total FNV: 285 points → Likely 4th-round comp pick
```

---

### Compensatory Pick Distribution

**Total Picks**: Maximum **32 compensatory picks** per year (one per team maximum base)

**Rounds**: Only rounds **3-7** (no 1st or 2nd round comp picks)

**Round Determination**:
- **Round 3**: Highest value losses (elite players, big contracts, high playing time)
- **Round 4**: High value losses
- **Round 5**: Medium value losses
- **Round 6**: Lower value losses
- **Round 7**: Lowest qualifying losses

**Position in Round**:
- Comp picks awarded at **end of each round**
- Ordered by FNV within each round (highest FNV first within comp picks)
- Example: Regular Round 3 picks 1-32, then Comp picks 33-40

**Maximum Per Team**: **4 compensatory picks** per team per year

---

### Net Loss Calculation

**Formula**:
```
Net CFA Loss = CFAs Lost - CFAs Gained

If Net CFA Loss > 0: Eligible for comp picks
If Net CFA Loss = 0: Eligible only if total FNV of losses > total FNV of gains
If Net CFA Loss < 0: NOT eligible (gained more than lost)
```

**Example Scenarios**:

**Scenario 1: Clear Net Loss**
```
Team A:
Lost: 3 CFAs (WR $15M, CB $12M, LB $8M)
Gained: 1 CFA (S $6M)

Net Loss: 3 - 1 = 2 CFAs
Eligible for: Likely 2 comp picks (based on WR and CB values)
```

**Scenario 2: Same Number, Higher Value Lost**
```
Team B:
Lost: 2 CFAs (DT $18M, RB $10M) = $28M total
Gained: 2 CFAs (CB $8M, TE $6M) = $14M total

Net Loss: 2 - 2 = 0, BUT total value lost > gained
Eligible for: 2 comp picks (higher total FNV lost)
```

**Scenario 3: More Gained (Not Eligible)**
```
Team C:
Lost: 1 CFA (WR $12M)
Gained: 3 CFAs (LB $10M, S $8M, DE $7M)

Net Loss: 1 - 3 = -2 CFAs
Eligible for: 0 comp picks (net gain, not loss)
```

---

### Special Rules & Exceptions

**10+ Year Veterans**:
- **5th Round Maximum**: Players with 10+ credited seasons capped at 5th-round comp value
- **Exception**: Quarterbacks exempt from this cap (can still earn 3rd/4th round)
- **Rationale**: Prevents huge comp picks for aging veterans on short contracts

**Cancellation Rule**:
- CFAs gained **cancel out** CFAs lost of similar value
- Net calculation inherently does this
- Important: Cannot get 5 comp picks by losing 6 and gaining 1

**Forfeiture**:
- **Tampering violations**: Can forfeit comp pick(s) as penalty
- **Salary cap violations**: May forfeit in settlement
- **Performance-based bonuses**: Comp picks cannot be traded until year awarded

---

### Strategic Implications

**For Teams Losing Players**:
- Develop talent → Lose to free agency → Get comp picks → Replenish via draft
- Model: Green Bay, Baltimore historically
- Accepts turnover to maintain draft capital

**For Teams Signing Players**:
- Be cautious with UFA signings → May cancel out comp picks from losses
- Target low-cost veterans or players coming off low snap count years
- Sign players who were cut (don't count as CFAs)

**For Released Players**:
- **Cut players DO NOT count** → Teams can release expensive veterans without comp pick penalty
- Common: Release aging veterans, sign younger veterans who were cut elsewhere

---

## Waiver System

### Purpose & Overview

The **waiver system** controls how teams can claim players who have been released, ensuring competitive balance by giving weaker teams priority access to released players.

### Waiver Priority Order

**Basic Principle**: Worst teams get first chance at claimed players

**Priority Determination**:

| Time Period | Priority Order |
|-------------|----------------|
| **Post-Super Bowl → Week 3** | Reverse draft order (previous year's standings) |
| **Week 4 → End of Season** | Reverse current season standings (updated weekly) |

**Important Notes**:
- Priority is **reverse order**: 32nd place team gets 1st waiver priority
- **One claim per waiver period**: If team claims player, they move to back of line for that waiver period
- **Weekly reset**: During regular season, waiver priority updates every Tuesday based on current standings

---

### Vested Veteran Rules

**Key Distinction**: Different waiver rules apply based on player experience and time of year

**Before Trade Deadline** (Before November 5):
- **Vested Veterans** (4+ accrued seasons): Do NOT go through waivers
  - Become **immediate unrestricted free agents**
  - Can sign with any team immediately
  - Team that released them has no priority
- **Non-Vested Players** (<4 accrued seasons): MUST go through waivers
  - Subject to waiver priority order
  - 24-hour waiver period

**After Trade Deadline** (November 5+):
- **ALL players** (including vested veterans) MUST go through waivers
- Prevents teams from strategically releasing players to specific destinations late in season
- Ensures competitive balance in playoff race

**Example**:
```
Scenario 1: October 15 (before trade deadline)
Team releases 8-year veteran QB with $20M salary

Result: QB becomes immediate free agent, can sign anywhere same day

Scenario 2: November 15 (after trade deadline)
Same team releases same QB

Result: QB goes on waivers for 24 hours, worst teams get first chance to claim
```

---

### Waiver Claiming Process

**Step 1: Player Released**
- Team waives/releases player
- Player enters waiver system (if non-vested OR after trade deadline)
- 24-hour waiver period begins

**Step 2: Claims Submitted**
- Teams submit waiver claims during 24-hour window
- Claims are blind (teams don't know who else is claiming)
- Multiple teams can claim same player

**Step 3: Priority Determination**
- If multiple claims: Team with highest priority (worst record) gets player
- If no claims: Player becomes free agent after 24 hours

**Step 4: Roster/Cap Requirements**
- **Claiming team MUST**:
  - Have open roster spot OR create one within 1 hour of claim being accepted
  - Have salary cap space for player's contract
  - Be willing to assume full contract terms

**Step 5: Contract Assumption**
- Claiming team takes on player's **existing contract**
- Cannot renegotiate until after season
- Releasing team off the hook for remaining salary (but dead money still applies)

---

### Final Roster Cuts (August 26)

**Special Waiver Period**: Most intense waiver activity of year

**Timeline**:
- **August 26, 4PM ET**: Deadline for teams to cut rosters to 53
- **August 26-27**: Waiver claims processed
- **August 27, 12PM ET**: Waiver claims awarded
- **August 27-28**: Teams fill practice squads (16 players)

**Claiming Strategy**:
- **High priority teams**: Can claim multiple players (don't move to back of line between cuts)
- **First year for rookie evaluation**: See which rookies/young players other teams value
- **Practice squad poaching**: After waivers clear, can sign players to practice squads

**Waiver Order** (August cuts):
- Based on **previous season's final standings** (since current season hasn't started)
- Reverse Super Bowl loser (1st priority) → Super Bowl winner (32nd priority)

---

### Strategic Considerations

**For Releasing Teams**:
- **Cut vested veterans early** (before Nov 5): Avoids waivers, player can choose destination
- **Cut vested veterans late** (after Nov 5): Goes through waivers, bad teams likely claim (prevents going to contender)
- **Minimize dead money**: Consider June 1 designations

**For Claiming Teams**:
- **Bad teams**: More likely to get waiver claims, but pay full contract
- **Good teams**: Lower priority, must wait until player clears waivers to sign
- **Young players**: Non-vested players must clear waivers even early season

**For Players**:
- **Vested status matters**: 4+ accrued seasons gives more control over destination
- **Timing of release**: Better to be cut before trade deadline (if vested) for freedom
- **Contract size**: Big contracts less likely to be claimed on waivers

---

## Negotiation & Market Factors

### How Teams Determine Player Value

NFL teams use sophisticated evaluation methods to determine how much to pay free agents. Understanding these helps simulate realistic contract negotiations.

### Primary Valuation Methods

#### 1. Positional Market Analysis

**Process**:
1. Identify player's position and role (QB1, CB1, slot WR, etc.)
2. Find recent contracts for comparable players (last 1-2 years)
3. Examine top contracts at position
4. Calculate market rate based on player's relative skill

**Key Comparables**:
- **Top 5 at position**: Elite tier contracts
- **Top 10 at position**: Pro Bowl/star contracts
- **Top 15-20**: Solid starter contracts
- **Top 25-32**: Below-average starter/high-end backup

**Positional Market Tiers** (2025 Approximate APY):

| Position | Elite (Top 3) | Star (Top 10) | Starter (Top 20) | Quality Backup |
|----------|---------------|---------------|------------------|----------------|
| **QB** | $50M+ | $35-45M | $25-32M | $8-15M |
| **RB** | $14-16M | $10-12M | $6-8M | $2-4M |
| **WR** | $28-32M | $20-25M | $12-18M | $5-8M |
| **TE** | $16-18M | $12-14M | $8-10M | $4-6M |
| **OT** | $23-27M | $18-22M | $12-16M | $6-10M |
| **OG/C** | $18-22M | $14-16M | $10-12M | $5-8M |
| **EDGE** | $26-30M | $20-24M | $14-18M | $6-10M |
| **DT** | $22-26M | $16-20M | $10-14M | $5-8M |
| **LB** | $20-24M | $14-18M | $10-12M | $4-7M |
| **CB** | $20-24M | $16-19M | $10-14M | $5-8M |
| **S** | $16-19M | $12-15M | $8-10M | $4-6M |

---

#### 2. Player-Specific Factors

**Age Curve**:
- **Prime years** (26-29): Maximum value, peak performance expected
- **Young veterans** (23-25): Ascending, potential for growth
- **Older veterans** (30-33): Declining, shorter contracts
- **Very old** (34+): Prove-it deals, likely one-year

**Production Metrics**:
- **Recent performance** (last 2 seasons weighted most)
- **Career trajectory**: Improving vs. declining
- **Durability**: Games missed due to injury
- **Consistency**: Year-to-year variance in stats

**Team Fit**:
- **Scheme fit**: Does player fit team's offensive/defensive system?
- **Positional need**: How desperate is team for this position?
- **Locker room**: Leadership, culture fit
- **Coaching staff familiarity**: Prior relationship with coaches

**Contract Leverage**:
- **Multiple suitors**: More teams interested = higher price
- **Franchise tag threat**: Can player be tagged instead?
- **Draft alternatives**: Could team draft this position instead?

---

#### 3. Adjusted APY Analysis

**Problem**: Salary cap increases yearly, so older contracts undervalue current market

**Solution**: Adjust past contracts for salary cap inflation

**Formula**:
```
Adjusted APY = (Original APY / Cap Year Signed) × Current Cap

Example:
2020 Contract: $15M APY when cap was $198M
2025 Adjusted: ($15M / $198M) × $255M = $19.3M equivalent
```

**Why This Matters**:
- $15M in 2020 was 7.6% of cap
- 7.6% of 2025 cap = $19.3M
- Player demanding "same relative value" should get $19.3M, not $15M

**Implementation**:
- Compare players as **percentage of salary cap** not absolute dollars
- Accounts for economic growth of league
- More accurate historical comparisons

---

### Contract Negotiation Process

#### Phase 1: Initial Interest (Legal Tampering Period)

**March 10-12** (48 hours before free agency opens)

**Activities**:
- Teams can **contact agents** but not players directly
- Can **negotiate terms** but not sign contracts
- Can **agree in principle** to deals
- **No binding agreements** can be made

**Strategic Timing**:
- Top free agents often have deals "agreed" before March 12
- Allows immediate signing when free agency opens
- Creates market-setting contracts early

---

#### Phase 2: Free Agency Opens (March 12, 4PM ET)

**First 24-48 Hours**:
- **Frenzy period**: Most top free agents sign within 48 hours
- **Market-setting deals**: First few contracts at each position set baseline
- **Team aggression**: Desperate teams overpay to land impact players
- **Media attention**: High public interest, pressure to make moves

**Strategic Decisions**:
- **Sign early**: Overpay for immediate impact (contending teams)
- **Wait for value**: Let market develop, sign discount veterans (rebuilding teams)

---

#### Phase 3: Post-Rush Period (Mid-March → April)

**Market Correction**:
- **Second-tier players** sign after top tier exhausted
- **Prove-it deals**: Players betting on themselves with one-year contracts
- **Value signings**: Teams fill depth at reasonable prices
- **Position scarcity**: If few QBs/OTs available, remaining ones get overpaid

---

#### Phase 4: Post-Draft (Late April → May)

**Veteran Signings**:
- Teams assess draft results and identify remaining needs
- Veterans who waited for "right situation" sign
- Often team-friendly deals (player missed first wave of money)

---

#### Phase 5: Training Camp (July → August)

**Desperation Signings**:
- Injury replacements
- Camp competition failures
- Last-minute depth additions
- Typically minimum salary or close to it

---

### Offer Structure Strategy

**For Players**:

**Maximize Guaranteed Money**:
- Prioritize fully guaranteed dollars over total contract value
- "$100M contract" means little if only $30M guaranteed
- Get money guaranteed at signing, not on future dates

**Contract Length**:
- **Longer (4-5 years)**: Security, but may limit future earning if player improves
- **Shorter (2-3 years)**: Get to free agency again sooner, risk if injured
- **One-year**: "Prove it" deal, bet on self to increase value

**Escalators & Incentives**:
- Add performance bonuses to increase total value
- Negotiate LTBE bonuses to help team's cap planning
- Include playing time bonuses for injury protection

---

**For Teams**:

**Cap Flexibility**:
- Large signing bonus spreads cap hit, creates Year 1 flexibility
- Low base salaries in early years
- Out clauses after Year 2-3 (can cut with minimal dead money)

**Performance Protection**:
- Minimal guarantees beyond Year 2
- De-escalators for missed games/poor performance
- Option years with reasonable salaries

**Position Value**:
- Pay premium for QB, EDGE, OT, CB (premium positions)
- Limit RB contracts (devalued position, short shelf life)
- Avoid guaranteed money Year 4+ for injury-prone positions

---

### Market Dynamics

**Supply & Demand**:
- **Weak FA class**: Average players get overpaid (scarcity)
- **Strong FA class**: Top players get paid, second tier gets less (oversupply)
- **Draft class strength**: Strong draft at position → lower FA prices

**Economic Factors**:
- **Cap increases**: More money available, prices rise
- **Cap decreases** (like 2021 COVID): Bidding wars rare, player-friendly market
- **Revenue growth**: Players get 48% of revenue → more total money available

**Positional Market Trends**:
- **Premium positions** rising: QB, OT, EDGE, CB increasing as % of cap
- **Devalued positions** falling: RB, LB decreasing as % of cap
- **Scheme evolution**: Slot WR, cover safety becoming more valuable

---

## Implementation Considerations

### Integration with Event-Based System

The free agency system integrates with the existing offseason event architecture (see `docs/plans/offseason_plan.md`).

#### Event Types for Free Agency

**DeadlineEvent Integration**:
```python
# Franchise Tag Deadline - March 4, 4PM ET
DeadlineEvent(
    deadline_type="FRANCHISE_TAG",
    deadline_date=datetime(2025, 3, 4, 16, 0, 0),
    actions_to_trigger=["check_franchise_tags", "apply_penalties_if_needed"]
)

# RFA Offer Sheet Deadline - April 22
DeadlineEvent(
    deadline_type="RFA_OFFER_SHEET",
    deadline_date=datetime(2025, 4, 22, 16, 0, 0),
    actions_to_trigger=["process_rfa_offers", "finalize_unsigned_rfas"]
)
```

**WindowEvent Integration**:
```python
# Legal Tampering Window
WindowEvent(window_type="LEGAL_TAMPERING", window_action="START",
            window_date=datetime(2025, 3, 10, 12, 0, 0))
WindowEvent(window_type="LEGAL_TAMPERING", window_action="END",
            window_date=datetime(2025, 3, 12, 16, 0, 0))

# Free Agency Signing Period
WindowEvent(window_type="FREE_AGENCY_SIGNING", window_action="START",
            window_date=datetime(2025, 3, 12, 16, 0, 0))
```

**ActionEvent Types**:
```python
# Franchise tag application
FranchiseTagEvent(team_id, player_id, tag_type, tag_date, season)

# UFA signing
UFASigningEvent(signing_team_id, player_id, contract_years,
                contract_value, signing_date, season)

# RFA offer sheet
RFAOfferSheetEvent(offering_team_id, player_id, contract_terms,
                   original_team_id, offer_date)

# RFA match response
RFAMatchEvent(original_team_id, player_id, match_decision, response_date)
```

---

### Database Schema Requirements

#### New Tables

**player_contracts**:
```sql
CREATE TABLE player_contracts (
    contract_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    contract_type TEXT, -- 'ROOKIE', 'VETERAN', 'FRANCHISE_TAG', 'TRANSITION_TAG'

    -- Contract Duration
    start_year INTEGER NOT NULL,
    end_year INTEGER NOT NULL,

    -- Financial Terms
    total_value INTEGER NOT NULL,
    signing_bonus INTEGER DEFAULT 0,

    -- Guarantees
    guaranteed_at_signing INTEGER DEFAULT 0,
    injury_guaranteed INTEGER DEFAULT 0,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    signed_date DATE,

    FOREIGN KEY (player_id) REFERENCES players(player_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);
```

**contract_year_details**:
```sql
CREATE TABLE contract_year_details (
    detail_id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL,
    contract_year INTEGER NOT NULL, -- 1, 2, 3, etc.
    season_year INTEGER NOT NULL,   -- 2025, 2026, etc.

    -- Salary Components
    base_salary INTEGER NOT NULL,
    roster_bonus INTEGER DEFAULT 0,
    workout_bonus INTEGER DEFAULT 0,
    option_bonus INTEGER DEFAULT 0,

    -- Guarantees for this year
    base_salary_guaranteed BOOLEAN DEFAULT FALSE,
    guarantee_type TEXT, -- 'FULL', 'INJURY', 'NONE'

    -- Cap Impact
    signing_bonus_proration INTEGER DEFAULT 0,
    total_cap_hit INTEGER,

    FOREIGN KEY (contract_id) REFERENCES player_contracts(contract_id)
);
```

**franchise_tags**:
```sql
CREATE TABLE franchise_tags (
    tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    tag_type TEXT NOT NULL, -- 'FRANCHISE_EXCLUSIVE', 'FRANCHISE_NON_EXCLUSIVE', 'TRANSITION'
    tag_salary INTEGER NOT NULL,
    tag_date DATE NOT NULL,
    extension_deadline DATE,
    is_extended BOOLEAN DEFAULT FALSE,

    FOREIGN KEY (player_id) REFERENCES players(player_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);
```

**rfa_tenders**:
```sql
CREATE TABLE rfa_tenders (
    tender_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    tender_level TEXT NOT NULL, -- 'FIRST_ROUND', 'SECOND_ROUND', 'ORIGINAL_ROUND', 'RIGHT_OF_FIRST_REFUSAL'
    tender_salary INTEGER NOT NULL,
    compensation_round INTEGER, -- NULL if right of first refusal only
    is_accepted BOOLEAN DEFAULT FALSE,
    has_offer_sheet BOOLEAN DEFAULT FALSE,

    FOREIGN KEY (player_id) REFERENCES players(player_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);
```

**rfa_offer_sheets**:
```sql
CREATE TABLE rfa_offer_sheets (
    offer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    offering_team_id INTEGER NOT NULL,
    original_team_id INTEGER NOT NULL,
    tender_id INTEGER NOT NULL,

    -- Offer Terms
    contract_years INTEGER NOT NULL,
    total_value INTEGER NOT NULL,
    guaranteed_money INTEGER NOT NULL,
    offer_date DATE NOT NULL,

    -- Status
    match_deadline DATE NOT NULL,
    is_matched BOOLEAN,
    match_decision_date DATE,

    FOREIGN KEY (player_id) REFERENCES players(player_id),
    FOREIGN KEY (offering_team_id) REFERENCES teams(team_id),
    FOREIGN KEY (original_team_id) REFERENCES teams(team_id),
    FOREIGN KEY (tender_id) REFERENCES rfa_tenders(tender_id)
);
```

**team_salary_cap**:
```sql
CREATE TABLE team_salary_cap (
    cap_id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    season INTEGER NOT NULL,

    -- Cap Limits
    salary_cap_limit INTEGER NOT NULL,

    -- Current Status
    active_contracts_total INTEGER DEFAULT 0,
    dead_money_total INTEGER DEFAULT 0,
    total_cap_used INTEGER GENERATED ALWAYS AS
        (active_contracts_total + dead_money_total) VIRTUAL,
    cap_space_available INTEGER GENERATED ALWAYS AS
        (salary_cap_limit - total_cap_used) VIRTUAL,

    -- Top 51 Rule (offseason)
    is_top_51_active BOOLEAN DEFAULT TRUE,
    top_51_total INTEGER DEFAULT 0,

    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    UNIQUE(team_id, season)
);
```

**compensatory_picks**:
```sql
CREATE TABLE compensatory_picks (
    comp_pick_id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    round_number INTEGER NOT NULL,
    pick_number_in_round INTEGER NOT NULL,
    overall_pick_number INTEGER,

    -- Attribution (which CFA loss caused this pick)
    attributed_player_id INTEGER,
    player_lost_to_team_id INTEGER,

    is_awarded BOOLEAN DEFAULT TRUE,
    is_forfeited BOOLEAN DEFAULT FALSE,

    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    FOREIGN KEY (attributed_player_id) REFERENCES players(player_id)
);
```

**free_agent_signings** (transaction log):
```sql
CREATE TABLE free_agent_signings (
    signing_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,

    -- Previous Team
    previous_team_id INTEGER,

    -- New Team
    new_team_id INTEGER NOT NULL,

    -- Contract Reference
    contract_id INTEGER NOT NULL,

    -- Signing Details
    signing_date DATE NOT NULL,
    free_agent_type TEXT, -- 'UFA', 'RFA', 'ERFA'

    -- CFA Status (for comp pick formula)
    is_compensatory_free_agent BOOLEAN DEFAULT FALSE,

    FOREIGN KEY (player_id) REFERENCES players(player_id),
    FOREIGN KEY (previous_team_id) REFERENCES teams(team_id),
    FOREIGN KEY (new_team_id) REFERENCES teams(team_id),
    FOREIGN KEY (contract_id) REFERENCES player_contracts(contract_id)
);
```

---

### AI Decision-Making Logic

#### AI Franchise Tag Decisions

```python
def should_franchise_tag_player(team, player, season):
    """
    Determine if AI team should use franchise tag on player.

    Returns: (should_tag: bool, tag_type: str)
    """

    # Check prerequisites
    if not player.is_pending_free_agent(season):
        return False, None

    if team.has_used_franchise_tag(season):
        return False, None  # Already used tag

    # Calculate player value metrics
    player_value = calculate_player_value(player)
    position_scarcity = get_position_scarcity(team, player.position)
    cap_space = team.get_cap_space(season)

    # Estimate franchise tag cost
    tag_cost = calculate_franchise_tag_salary(player.position, season)

    # Decision factors
    if player_value >= 85:  # Elite player (85+ overall)
        if cap_space >= tag_cost * 1.2:
            # Can afford, high value player
            if position_scarcity >= 0.7:  # Critical need
                return True, "FRANCHISE_EXCLUSIVE"
            else:
                return True, "FRANCHISE_NON_EXCLUSIVE"

    elif player_value >= 80:  # Star player (80-84 overall)
        if cap_space >= tag_cost * 1.5:
            # Only tag if have extra space (not desperate)
            if position_scarcity >= 0.8:
                return True, "FRANCHISE_NON_EXCLUSIVE"

    return False, None
```

#### AI Free Agency Bidding

```python
def evaluate_free_agent_target(team, free_agent, season):
    """
    Determine if AI team should pursue free agent and calculate offer.

    Returns: (pursue: bool, max_offer: dict)
    """

    # Team need assessment
    position_need = assess_position_need(team, free_agent.position)
    if position_need < 0.5:  # Low need (0-1 scale)
        return False, None

    # Cap space check
    cap_space = team.get_cap_space(season)
    if cap_space < 5_000_000:  # Need minimum $5M space
        return False, None

    # Player evaluation
    player_value = calculate_player_value(free_agent)
    player_age = free_agent.age
    position_market = get_position_market_rates(free_agent.position, season)

    # Calculate appropriate offer
    market_rate = position_market.get_rate_for_value(player_value)

    # Age adjustment
    if player_age >= 30:
        market_rate *= 0.85  # 15% discount for age
        max_years = 2
    elif player_age >= 28:
        market_rate *= 0.95  # 5% discount
        max_years = 3
    else:
        max_years = 4

    # Need adjustment
    if position_need >= 0.8:  # Desperate need
        market_rate *= 1.15  # 15% premium

    # Cap space constraint
    max_apy = min(market_rate, cap_space * 0.25)  # Max 25% of cap space

    max_offer = {
        "apy": max_apy,
        "years": max_years,
        "total_value": max_apy * max_years,
        "guaranteed": max_apy * min(2, max_years)  # Guarantee first 2 years
    }

    return True, max_offer
```

#### AI RFA Tender Decisions

```python
def determine_rfa_tender_level(team, rfa_player, season):
    """
    Decide which RFA tender to offer (if any).

    Returns: tender_level (str or None)
    """

    # Evaluate player
    player_value = calculate_player_value(rfa_player)
    draft_round = rfa_player.draft_round  # Which round drafted

    # Get tender costs
    first_round_cost = 7_458_000
    second_round_cost = 5_346_000
    original_round_cost = 3_406_000
    rofr_cost = 3_263_000

    cap_space = team.get_cap_space(season)

    # Decision matrix
    if player_value >= 82:  # Very good player
        if cap_space >= first_round_cost:
            return "FIRST_ROUND"  # Max protection
        elif cap_space >= second_round_cost:
            return "SECOND_ROUND"  # Still good protection

    elif player_value >= 75:  # Solid starter
        if draft_round <= 2:  # High pick originally
            if cap_space >= second_round_cost:
                return "SECOND_ROUND"
        else:
            if cap_space >= original_round_cost:
                return "ORIGINAL_ROUND"

    elif player_value >= 70:  # Depth player worth keeping
        if cap_space >= rofr_cost:
            return "RIGHT_OF_FIRST_REFUSAL"

    # Don't tender (let become UFA)
    return None
```

---

### User Interaction Points

#### Free Agency Dashboard

```
╔═══════════════════════════════════════════════════════════╗
║                  FREE AGENCY CENTER                        ║
╠═══════════════════════════════════════════════════════════╣
║                                                            ║
║  Phase: Free Agency Open (Day 3)                          ║
║  Date: March 14, 2025                                     ║
║                                                            ║
║  💰 SALARY CAP STATUS                                      ║
║  ┌────────────────────────────────────────────────────┐  ║
║  │ Cap Space: $32.5M        Top 51: $222.5M          │  ║
║  │ Active Contracts: 48     Cap Limit: $255M         │  ║
║  └────────────────────────────────────────────────────┘  ║
║                                                            ║
║  🏈 YOUR PENDING FREE AGENTS (4)                          ║
║  ┌────────────────────────────────────────────────────┐  ║
║  │ 1. WR Calvin Johnson (85 OVR) - UFA               │  ║
║  │    Interest: HIGH | Est. Market: $18M/year        │  ║
║  │    [Re-sign] [Let Walk] [Franchise Tag]           │  ║
║  │                                                     │  ║
║  │ 2. LB Patrick Willis (82 OVR) - RFA               │  ║
║  │    Your Tender: 2nd Round ($5.3M)                 │  ║
║  │    Status: No offer sheets yet                     │  ║
║  └────────────────────────────────────────────────────┘  ║
║                                                            ║
║  🔍 AVAILABLE FREE AGENTS                                 ║
║  [Browse by Position] [View Top 100] [Search]            ║
║                                                            ║
║  📰 RECENT SIGNINGS (League-Wide)                         ║
║  ┌────────────────────────────────────────────────────┐  ║
║  │ • QB Russell Wilson → Broncos (5yr, $245M)        │  ║
║  │ • EDGE Von Miller → Bills (6yr, $120M)            │  ║
║  │ • CB Darrelle Revis → Patriots (3yr, $48M)        │  ║
║  └────────────────────────────────────────────────────┘  ║
║                                                            ║
║  ACTIONS                                                   ║
║  [1] Browse Free Agents  [2] Make Offer                   ║
║  [3] Manage Your FAs     [4] View Transactions            ║
║  [5] Advance 1 Day       [0] Exit                         ║
╚═══════════════════════════════════════════════════════════╝
```

#### Contract Offer Interface

```
╔═══════════════════════════════════════════════════════════╗
║              CONTRACT OFFER - WR CALVIN JOHNSON            ║
╠═══════════════════════════════════════════════════════════╣
║                                                            ║
║  Player Info: WR Calvin Johnson (Age 29, 85 OVR)         ║
║  Current Team: Detroit Lions                              ║
║  Status: Unrestricted Free Agent                          ║
║                                                            ║
║  Market Analysis:                                          ║
║  • Estimated Market Value: $16-20M/year                   ║
║  • Top WR Contracts: $28M, $25M, $22M (recent)           ║
║  • Your Position Need: HIGH (no WR1 on roster)           ║
║                                                            ║
║  ═══════════════════════════════════════════════════════  ║
║                                                            ║
║  YOUR OFFER:                                               ║
║                                                            ║
║  Contract Length: [▼ 4 years ]                            ║
║                                                            ║
║  Average Per Year: $_______________  (Enter amount)       ║
║                                                            ║
║  Signing Bonus: $_______________                          ║
║                                                            ║
║  Guaranteed Money: $_______________                       ║
║                                                            ║
║  ═══════════════════════════════════════════════════════  ║
║                                                            ║
║  Offer Preview:                                            ║
║  ┌────────────────────────────────────────────────────┐  ║
║  │ Year 1: $_____ base + $____ bonus = $____ cap hit │  ║
║  │ Year 2: $_____ base + $____ bonus = $____ cap hit │  ║
║  │ Year 3: $_____ base + $____ bonus = $____ cap hit │  ║
║  │ Year 4: $_____ base + $____ bonus = $____ cap hit │  ║
║  │                                                     │  ║
║  │ Total Value: $________                             │  ║
║  │ Guaranteed: $________                              │  ║
║  │ Cap Space After: $________                         │  ║
║  └────────────────────────────────────────────────────┘  ║
║                                                            ║
║  [Submit Offer] [Use Market Rate] [Cancel]                ║
╚═══════════════════════════════════════════════════════════╝
```

---

## Simulation Simplifications

### Recommended Simplifications for Gameplay

While the NFL's free agency system is complex, certain aspects can be simplified for better gameplay without sacrificing realism.

#### Level 1: Simplified (Quick Play)

**Contract Structure**:
- **Single guaranteed amount** (no skill/injury/cap distinctions)
- **No performance bonuses** (base + signing bonus only)
- **Automatic proration** (system handles cap math)
- **Standard contract lengths** (2-3 year deals for most positions)

**Franchise Tags**:
- **Single tag type** (combine franchise + transition into one "tag")
- **Auto-calculated salary** (system sets based on position)
- **No consecutive tag penalties** (same cost each year)

**RFA System**:
- **Two tender levels** (Original Round + Right of First Refusal only)
- **Simplified matching** (AI auto-matches if cap space available)

**Free Agency**:
- **Position-based markets** (QB tier, WR tier, etc.)
- **Age-adjusted offers** (younger = longer contracts automatically)
- **Quick sim mode** (advance week-by-week, see results)

**Benefits**:
- Faster gameplay, less micromanagement
- Focus on team-building strategy vs. cap minutiae
- New players can learn system quickly

---

#### Level 2: Realistic (Standard Mode)

**Contract Structure**:
- **Guaranteed money matters** (total vs. guaranteed distinct)
- **Signing bonuses** (proration handled, affects dead money)
- **Roster bonuses** (March bonuses create cut decisions)
- **Simplified performance bonuses** (3-4 categories: Pro Bowl, snaps, stats)

**Franchise Tags**:
- **Two tag types** (Franchise + Transition, but combine exclusive/non-exclusive)
- **Draft pick compensation** (matters for strategic decisions)
- **Consecutive tag escalators** (gets expensive to tag multiple years)

**RFA System**:
- **All four tender levels** (full complexity)
- **Offer sheet system** (user can submit, AI teams evaluate)
- **5-day matching window** (simulated, user gets notification)

**Free Agency**:
- **Market dynamics** (early vs. late signings, positional scarcity)
- **Negotiation factors** (fit, need, competition affect price)
- **Compensatory picks** (CFAs matter for draft capital)

**Benefits**:
- Authentic NFL experience
- Strategic depth for experienced players
- Real consequences for decisions (dead money, comp picks)

---

#### Level 3: Deep Simulation (Franchise Mode)

**Contract Structure**:
- **Full guarantee types** (skill, injury, cap all tracked)
- **All bonus types** (roster, workout, option, performance)
- **LTBE vs NLTBE** (affects cap planning)
- **Contract restructures** (user can initiate mid-contract)

**Franchise Tags**:
- **All tag types** (exclusive vs. non-exclusive matters)
- **Extension negotiations** (July deadline creates urgency)
- **Offer sheet mechanics** (if non-exclusive, other teams can bid)

**RFA System**:
- **Full tender system** (including original round varies by draft round)
- **Comp pick trading** (can forfeit/gain in negotiations)

**Free Agency**:
- **Advanced AI** (teams have strategies: aggressive, patient, value-seeking)
- **Negotiation mini-game** (back-and-forth with agents)
- **Compensatory pick formula** (APY + snaps + honors calculated)
- **Waiver priority** (matters for in-season moves)

**Benefits**:
- Maximum realism for hardcore sim players
- Deep dynasty mode possibilities
- Every NFL rule implemented

---

### Recommended Abstractions

**Always Abstract** (even in Deep Simulation):

1. **Agent Negotiations**:
   - Don't simulate agent-team relationship drama
   - Abstract to: "Player wants X, will accept Y"

2. **Medical Examinations**:
   - Don't fail physicals in free agency
   - Assume all signings pass medical

3. **Contract Language**:
   - Don't simulate offset language, void years, etc.
   - Focus on: AAV, guarantees, length

4. **Workout Bonuses**:
   - Can skip entirely or auto-grant
   - Minimal gameplay impact

5. **Minor Bonuses**:
   - Don't track $50K bonuses for individual stats
   - Bundle into "performance bonus pool"

**Performance vs. Realism Trade-offs**:

| Feature | Realism Value | Performance Cost | Recommendation |
|---------|---------------|------------------|----------------|
| Full guarantee types | Medium | Low | Include (Standard+) |
| LTBE vs NLTBE | Low | Medium | Skip (Deep only) |
| Compensatory formula | Medium | Medium | Include (Standard+) |
| Contract restructures | High | Low | Include (Standard+) |
| Workout bonuses | Very Low | Low | Skip (all modes) |
| Draft pick trading in RFA | Low | Low | Skip (Deep only) |
| Waiver priority | Medium | Low | Include (Standard+) |
| June 1 designations | Medium | Low | Include (Realistic+) |

---

## Reference Data Tables

### 2025 Minimum Salaries by Experience

| Experience (Credited Seasons) | 2025 Minimum Salary |
|------------------------------|---------------------|
| 0 (Rookie) | $795,000 |
| 1 | $915,000 |
| 2 | $1,005,000 |
| 3 | $1,080,000 |
| 4-6 | $1,165,000 |
| 7-9 | $1,250,000 |
| 10+ | $1,365,000 |

**Veteran Salary Benefit**: 4+ year veterans count as **$915,000** (Year 1 minimum) against cap

---

### 2025 RFA Tender Amounts

| Tender Level | 2025 Salary | Compensation |
|--------------|-------------|--------------|
| First-Round Tender | $7,458,000 | Original 1st-round pick |
| Second-Round Tender | $5,346,000 | Original 2nd-round pick |
| Original-Round Tender | $3,406,000 | Draft round player was selected |
| Right of First Refusal | $3,263,000 | None |

*All amounts are "OR 110% of previous salary, whichever is greater"*

---

### 2025 Franchise Tag Estimates by Position

| Position | Non-Exclusive Tag | Exclusive Tag | Transition Tag |
|----------|------------------|---------------|----------------|
| QB | $31,800,000 | $33,500,000 | $28,500,000 |
| RB | $12,100,000 | $13,000,000 | $10,500,000 |
| WR | $21,800,000 | $22,500,000 | $19,200,000 |
| TE | $14,200,000 | $15,100,000 | $12,800,000 |
| OT | $20,500,000 | $21,300,000 | $18,700,000 |
| OG/C | $16,500,000 | $17,200,000 | $15,000,000 |
| EDGE/DE | $19,800,000 | $20,600,000 | $17,900,000 |
| DT | $18,300,000 | $19,100,000 | $16,500,000 |
| LB | $16,700,000 | $17,500,000 | $15,000,000 |
| CB | $19,000,000 | $19,800,000 | $17,200,000 |
| S | $14,800,000 | $15,500,000 | $13,400,000 |
| K | $5,400,000 | $5,700,000 | $4,800,000 |
| P | $4,900,000 | $5,200,000 | $4,400,000 |

*These are approximate 2025 values and will fluctuate based on new contracts*

---

### Practice Squad Salaries (2025)

| Experience Level | Weekly Salary | Full Season (18 weeks) |
|------------------|---------------|------------------------|
| 0-1 Accrued Seasons | $13,000 | $234,000 |
| 2+ Accrued Seasons (Min) | $17,500 | $315,000 |
| 2+ Accrued Seasons (Max) | $22,000 | $396,000 |

**Practice Squad Rules**:
- 16 players maximum (17 with International Pathway)
- Maximum 10 players with 2 or fewer accrued seasons
- Maximum 6 players with unlimited experience
- Salaries do NOT count against salary cap

---

### Key Dates Quick Reference (2025)

| Date | Event |
|------|-------|
| **Feb 9** | Super Bowl LIX |
| **Feb 17** | Franchise tag window opens |
| **March 4, 4PM ET** | **Franchise tag deadline** |
| **March 10, 12PM ET** | **Legal tampering begins** |
| **March 12, 4PM ET** | **New league year / Free agency opens** |
| **April 22** | **RFA offer sheet deadline** |
| **April 24-26** | **NFL Draft** |
| **May 2** | **5th-year option deadline** |
| **Mid-July** | Franchise tag extension deadline |
| **July 16+** | Training camps open |
| **August 26, 4PM ET** | **Final roster cuts (53-man)** |
| **August 27, 12PM ET** | **Waiver claim deadline** |
| **September 4** | Regular season begins |
| **November 5** | **Trade deadline** (vested veteran waiver rule changes) |

---

## Appendix: Example Contract Structures

### Example 1: Elite QB Contract

**Player**: Top-5 QB, Age 28
**Market**: $50M/year

```
5-Year, $250M Contract

Year 1:
  Base Salary: $10M (fully guaranteed)
  Signing Bonus: $50M (prorated $10M/year)
  Cap Hit: $20M

Year 2:
  Base Salary: $45M (fully guaranteed)
  Signing Bonus Proration: $10M
  Cap Hit: $55M

Year 3:
  Base Salary: $55M (becomes guaranteed March 2027)
  Signing Bonus Proration: $10M
  Cap Hit: $65M

Year 4:
  Base Salary: $60M (not guaranteed)
  Signing Bonus Proration: $10M
  Cap Hit: $70M

Year 5:
  Base Salary: $70M (not guaranteed)
  Signing Bonus Proration: $10M
  Cap Hit: $80M

Total Value: $250M
Guaranteed at Signing: $105M ($10M + $45M + $50M bonus)
Practical Guaranteed: $165M (includes Year 3 if kept)
```

**Strategic Analysis**:
- Massive signing bonus creates cap flexibility in Year 1
- Years 4-5 are "team option" years (can cut with only dead money from bonus)
- $50M in dead money if cut before Year 3

---

### Example 2: Mid-Tier WR Contract

**Player**: WR2/Borderline WR1, Age 26
**Market**: $18M/year

```
4-Year, $72M Contract

Year 1:
  Base Salary: $8M (fully guaranteed)
  Signing Bonus: $20M (prorated $5M/year)
  Roster Bonus (March 15): $2M
  Cap Hit: $15M

Year 2:
  Base Salary: $15M (fully guaranteed)
  Signing Bonus Proration: $5M
  Cap Hit: $20M

Year 3:
  Base Salary: $20M (injury guaranteed only)
  Signing Bonus Proration: $5M
  Cap Hit: $25M

Year 4:
  Base Salary: $22M (not guaranteed)
  Signing Bonus Proration: $5M
  Cap Hit: $27M

Total Value: $72M ($18M APY)
Guaranteed at Signing: $45M ($8M + $15M + $20M bonus + $2M roster)
Out After Year 2: $10M dead money (2 years bonus remaining)
```

---

### Example 3: Prove-It Deal (One-Year)

**Player**: Veteran coming off injury, Age 30
**Market**: Uncertain, betting on self

```
1-Year, $8M Contract

Base Salary: $6M (fully guaranteed)
Signing Bonus: $2M
Playing Time Bonus: $2M (if 75%+ snaps - NLTBE)
Pro Bowl Bonus: $1M (NLTBE)

Cap Hit: $8M
Potential Max Value: $11M
Guaranteed: $8M

Benefits for Player:
- All money guaranteed (low risk)
- Can reach free agency next year if plays well
- Bonuses increase earning potential

Benefits for Team:
- Short commitment (can move on after 1 year)
- Performance upside (bonuses only if he produces)
- Low risk if injury recurs
```

---

## Conclusion

This specification provides the foundation for implementing a realistic NFL free agency system that balances authenticity with playability. The system integrates with the existing event-based offseason architecture and supports multiple levels of simulation depth to accommodate different player preferences.

**Key Implementation Priorities**:

1. **Phase 1**: Core free agent types and contract basics
2. **Phase 2**: Franchise tag and RFA tender systems
3. **Phase 3**: Salary cap tracking and compliance
4. **Phase 4**: AI decision-making for all 32 teams
5. **Phase 5**: User interface and interaction
6. **Phase 6**: Compensatory picks and advanced features

For integration with the broader offseason system, see `docs/plans/offseason_plan.md`.

---

**Document Version History**:
- **v1.0** (October 4, 2025): Initial specification based on 2025 NFL rules

**References**:
- NFL Football Operations: 2025 Free Agency Questions & Answers
- NFL Collective Bargaining Agreement (2020-2030)
- Over the Cap: Franchise Tags, RFA Tenders, Compensatory Formula
- Pro Football Network: Salary Cap Explainers
