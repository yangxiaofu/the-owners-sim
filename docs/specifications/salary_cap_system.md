# NFL Salary Cap System - Technical Specification

**Version**: 1.0
**Date**: October 4, 2025
**Status**: Reference Documentation
**Based on**: 2024-2025 NFL Collective Bargaining Agreement

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Salary Cap Fundamentals](#salary-cap-fundamentals)
3. [Contract Components](#contract-components)
4. [Cap Accounting Mechanisms](#cap-accounting-mechanisms)
5. [Roster Rules and Compliance](#roster-rules-and-compliance)
6. [Player Tags](#player-tags)
7. [Minimum Salaries and Rookie Contracts](#minimum-salaries-and-rookie-contracts)
8. [Practice Squad](#practice-squad)
9. [Cap Management Strategies](#cap-management-strategies)
10. [Penalties and Violations](#penalties-and-violations)
11. [Implementation Considerations](#implementation-considerations)

---

## Executive Summary

The NFL salary cap is a comprehensive financial system that limits how much each team can spend on player salaries in a given season. The system is designed to promote competitive balance by preventing wealthy teams from dominating through superior financial resources.

### Key 2025 Figures

- **Salary Cap**: $279.2 million per team
- **Increase from 2024**: $23.8 million (from $255.4M)
- **Rookie Minimum Salary**: $840,000
- **Practice Squad Weekly (0-1 years)**: $13,000

### Core Principle

**Cash vs Cap**: Cash is real money paid to players; cap is accounting. A team can pay $20M in signing bonus cash but spread it as $4M/year over 5 years for cap purposes.

---

## Salary Cap Fundamentals

### 1. Cap Determination

The salary cap is determined by a Collective Bargaining Agreement (CBA) between the NFL and NFL Players Association (NFLPA) based on league revenue.

**Revenue Sources:**
- Media rights deals
- Sponsorship and advertising
- Merchandise sales
- Ticket sales

**Revenue Split:**
- The CBA establishes a revenue-sharing formula between owners and players
- Cap increases correlate with league revenue growth

### 2. Compliance Requirements

**Annual Compliance:**
- Teams must be cap-compliant at the start of the league year (4:00 PM ET, second Wednesday in March)
- Teams must remain compliant throughout the season

**Four-Year Spending Floor:**
- Every team must spend at least **89% of the salary cap** over a four-year period
- This is measured in **CASH**, not cap accounting
- Prevents teams from consistently underspending

**Example:**
```
4-year period cap total: $1 billion
Minimum cash spending: $890 million
```

### 3. Carryover Cap Space

**100% Rollover Rule:**
- Teams can carry over 100% of unused cap space from the previous year
- This rewards fiscal discipline and adds flexibility

**Example:**
```
2024 Cap: $255.4M
Team Spending: $245.4M
Unused Space: $10M

2025 Cap: $279.2M
Carryover: $10M
Total Available: $289.2M
```

### 4. What Counts Against the Cap

**Included:**
- All player salaries and bonuses (prorated)
- Dead money from released/traded players
- Practice squad salaries
- Top-51 contracts during offseason

**Excluded:**
- Coaching staff salaries
- Front office personnel
- Stadium and facility costs
- Medical staff salaries

---

## Contract Components

### 1. Base Salary

**Definition:** Annual salary earned for being on the roster during the season.

**Characteristics:**
- Paid in 17 weekly installments during regular season
- Can be guaranteed or non-guaranteed
- Counts against cap in the year earned
- Most common contract component

**Cap Impact:** 100% of base salary counts against cap in that season

**Example:**
```
Year 1 Base Salary: $5,000,000
Cap Hit Year 1: $5,000,000
Cash Paid: 17 payments of $294,118
```

### 2. Signing Bonus

**Definition:** One-time payment made when contract is signed.

**Characteristics:**
- **Always fully guaranteed**
- Paid to player immediately (within 15 days or first year)
- **Prorated** over contract length (max 5 years) for cap purposes
- Key tool for cap manipulation

**Cap Impact:** Divided equally over contract years (maximum 5)

**Example:**
```
4-year contract, $20M signing bonus:
- Cash paid to player: $20M (Year 1)
- Cap hit per year: $5M (Years 1-4)
- Cash over cap in Year 1: $15M
```

**Proration Rules:**
- Maximum proration period: 5 years
- If contract is 6 years, bonus prorates over 5 years
- Remaining proration accelerates if player is released (becomes dead money)

### 3. Roster Bonus

**Definition:** Conditional bonus tied to being on roster on specific date.

**Types:**

**A. Offseason Roster Bonus:**
- Tied to being on roster on specific date (usually 3-5 days after league year starts)
- Common dates: Late March
- Counts against cap in year earned
- Can be guaranteed or non-guaranteed

**B. Per-Game Roster Bonus:**
- Paid for each game player is on active 53-man roster
- Calculated as total bonus ÷ 17 games
- Incentivizes staying healthy and active

**Cap Impact:** Full amount counts in year earned (not prorated)

**Example:**
```
Per-Game Roster Bonus: $170,000
Per Game Payment: $10,000
Active for 15 games: $150,000 paid
Cap Hit: $150,000 (only for games active)
```

### 4. Workout Bonus

**Definition:** Compensation for attending voluntary offseason workouts (OTAs).

**Characteristics:**
- Typical range: $50,000 - $250,000
- Tied to attendance percentage (e.g., 80% of OTAs)
- Voluntary nature but financial incentive
- Common for veteran contracts

**Cap Impact:** Counts in year earned if conditions met

### 5. Incentives

**Definition:** Performance-based bonuses tied to individual or team achievements.

**Types:**

**A. Likely To Be Earned (LTBE):**
- Based on **prior year performance**
- Player or team achieved metric last season
- **Counts against current year cap**
- If not achieved, cap credit applied next year

**B. Not Likely To Be Earned (NLTBE):**
- Player or team did NOT achieve metric last season
- **Does NOT count against current year cap**
- If achieved, counts against next year's cap

**Common Incentive Types:**
- Playing time (e.g., 70% of snaps)
- Statistical milestones (1,000 yards, 10 TDs)
- Team achievements (playoff appearance, division win)
- Individual honors (Pro Bowl, All-Pro)

**Example:**
```
Player rushed for 1,200 yards in 2024
2025 Incentive: $500,000 for 1,000 rushing yards

Classification: LTBE (achieved last year)
2025 Cap Hit: $500,000 (charged upfront)

Outcomes:
- Achieves 1,000 yards: No adjustment
- Falls short: $500,000 cap credit in 2026
```

### 6. Option Bonuses

**Definition:** Bonus paid when team exercises contract option.

**Characteristics:**
- Treated like signing bonus (can be prorated)
- Gives team flexibility to extend or release
- Common in veteran contracts
- Proration follows signing bonus rules (max 5 years)

---

## Cap Accounting Mechanisms

### 1. Bonus Proration

**Core Concept:** Signing bonuses and option bonuses are spread evenly over contract years for cap purposes, even though cash is paid immediately.

**Proration Formula:**
```
Annual Cap Charge = Total Bonus ÷ MIN(Contract Years, 5)
```

**Example 1: Standard Proration**
```
Contract: 4 years, $16M signing bonus
Annual Proration: $16M ÷ 4 = $4M per year

Year 1: $4M cap hit (player receives $16M cash)
Year 2: $4M cap hit
Year 3: $4M cap hit
Year 4: $4M cap hit
```

**Example 2: 5-Year Maximum**
```
Contract: 7 years, $35M signing bonus
Annual Proration: $35M ÷ 5 = $7M per year (NOT 7 years)

Years 1-5: $7M cap hit each year
Years 6-7: $0 from signing bonus
```

### 2. Dead Money

**Definition:** Cap charges for players no longer on the roster due to remaining signing bonus proration.

**When It Occurs:**
- Player is released
- Player is traded (can be split or absorbed)
- Player retires (team can pursue recovery of bonuses)

**Acceleration Rule:**
- All remaining proration accelerates to current year's cap
- Exception: June 1 designation (see below)

**Example:**
```
4-year deal, $20M signing bonus ($5M/year proration)
Player released after Year 2

Dead Money Calculation:
- Years 3-4 remaining: 2 × $5M = $10M
- Dead money cap hit in Year 3: $10M
- Team gains cap relief from base salary
```

**Real-World Example (2024):**
- Denver Broncos released Russell Wilson
- Dead cap hit: $85 million
- One of largest dead money charges in NFL history

### 3. June 1 Designations

**Purpose:** Spread dead money cap hit over two years instead of one.

**Rules:**
- Team can designate up to **2 players per year** as "June 1" releases
- Can be designated any time, doesn't have to wait until June 1
- Actual designation can occur in March, but accounting follows June 1 rules

**Cap Treatment:**
- **Current year:** One year of proration (same as if player stayed)
- **Next year:** Remaining proration accelerates

**Example:**
```
4-year deal, $20M signing bonus ($5M/year)
Player released after Year 2 with June 1 designation

Standard Release:
Year 3 dead money: $10M (all at once)

June 1 Release:
Year 3 dead money: $5M (one year of proration)
Year 4 dead money: $5M (remaining proration)

Benefit: Spreads $10M cap hit over 2 years
```

**Strategic Use:**
- Creates cap space in current year
- Pushes problem to next year
- Limited to 2 players per year
- Useful when team needs immediate cap relief

### 4. Contract Restructuring

**Definition:** Converting base salary (or roster/workout bonus) into signing bonus to reduce current year cap hit.

**Mechanism:**
1. Team pays player guaranteed money immediately
2. Amount is treated as "new" signing bonus
3. New bonus is prorated over remaining contract years (max 5)

**Cap Benefit:** Immediate cap savings in current year

**Long-Term Cost:** Increased future cap hits and dead money risk

**Example:**
```
Original Contract (Year 2 of 4):
Year 2 Base Salary: $15M
Cap Hit: $15M

Restructure:
Convert $12M of base salary to signing bonus
New Base Salary: $3M
New Signing Bonus: $12M (prorated over 3 remaining years)

New Year 2 Cap Hit:
Base Salary: $3M
Bonus Proration: $12M ÷ 3 = $4M
Total: $7M

Cap Savings: $15M - $7M = $8M in Year 2

Future Impact:
Years 3-4: Additional $4M cap hit each year from restructure
If released after Year 2: $8M dead money from restructure
```

**Common Scenario:**
- "Kicking the can down the road"
- Creates current year flexibility
- Increases future cap obligations
- Used by teams in "win now" mode

### 5. Void Years

**Definition:** Dummy contract years used for cap accounting that automatically void.

**Purpose:** Spread bonus proration over more years to reduce annual cap hit.

**How They Work:**
1. Contract includes years that automatically void
2. Signing bonus prorates over all years (including void years)
3. When void years trigger, remaining proration becomes dead money
4. Player becomes free agent when contract voids

**Example:**
```
3-year contract with 2 void years (5 years total for accounting)
Signing Bonus: $25M

Cap Accounting:
Years 1-3: $5M proration per year ($25M ÷ 5)
Year 4: Contract voids, $10M dead money (2 years × $5M)

Without Void Years:
Years 1-3: $8.33M proration per year ($25M ÷ 3)

Benefit: Saves $3.33M per year in Years 1-3
Cost: $10M dead money in Year 4
```

**Strategic Use:**
- Lower annual cap hits during contract
- Pushes dead money to future year
- Player can be re-signed before void triggers
- Common in recent years for cap manipulation

---

## Roster Rules and Compliance

### 1. Top-51 Rule (Offseason)

**Period:** From day after Super Bowl until first game of regular season

**Rule:** Only the **top 51 cap hits** count against the salary cap

**Purpose:**
- Allows teams to carry 90-man offseason rosters
- Bottom 39 contracts don't count against cap
- Provides flexibility for camp bodies and tryouts

**Example:**
```
Offseason Roster: 90 players
Top 51 contracts: Count against cap
Bottom 39 contracts: Do not count against cap

When calculating cap space: Only top 51 matter
```

**Strategic Implications:**
- Signing minimum salary players has minimal cap impact
- Rookie draft picks replace lower-paid players in top 51
- Each rookie effectively costs (rookie salary - displaced player salary)

**Rookie Draft Impact Example:**
```
Top 51 includes player making $900,000
Draft rookie with $1.5M cap hit

Net Cap Impact: $1.5M - $0.9M = $600,000
(Not full $1.5M because lowest-paid player drops out of top 51)
```

### 2. 53-Man Roster (Regular Season)

**Period:** Regular season and playoffs

**Rule:** All 53 active roster players count against cap

**Weekly Adjustments:**
- Activating practice squad player: Full cap hit for that week
- Placing player on IR: Cap hit remains unless released
- Suspensions: Cap relief for suspended weeks

### 3. Injured Reserve (IR)

**Cap Treatment:**
- Player remains on contract
- Full cap hit continues
- No cap relief unless player is released with injury settlement

**IR Rules:**
- Season-ending IR: Player can't return that season
- Short-term IR: Player can return after 4 weeks
- Unlimited returns allowed (changed from old rules)

### 4. Physically Unable to Perform (PUP)

**Preseason PUP:**
- Doesn't count against 90-man roster
- Can be activated any time in preseason
- Full cap hit once activated

**Regular Season PUP:**
- Counts against 53-man roster
- Player must miss first 4 games
- Full cap hit throughout

---

## Player Tags

### 1. Franchise Tag

**Definition:** One-year tender preventing unrestricted free agency.

**Two Types:**

**A. Exclusive Franchise Tag:**
- Player cannot negotiate with other teams
- Guaranteed salary: Average of top 5 salaries at position
- No compensation if player leaves (because he can't)
- Rarely used due to high cost

**B. Non-Exclusive Franchise Tag:**
- Player can negotiate with other teams
- Original team has right to match any offer
- If team declines to match: Receives **two first-round draft picks** as compensation
- Guaranteed salary: Average of top 5 salaries at position OR 120% of previous year salary (whichever is greater)

**2025 Tag Amounts by Position (Estimated):**
```
QB: ~$35-40M
RB: ~$12-14M
WR: ~$20-25M
TE: ~$15-18M
OL: ~$18-22M
DL: ~$20-25M
LB: ~$18-22M
CB: ~$20-25M
S: ~$15-18M
K/P: ~$5-6M
```

**Usage Rules:**
- Each team can use **one tag per year** (franchise OR transition, not both)
- Tag can be used on same player multiple years
- **Successive tags increase cost:**
  - 1st tag: Top 5 average
  - 2nd tag: 120% of previous tag
  - 3rd tag: 144% of previous tag (or QB top 5 average, whichever is greater)

**Example - Multiple Year Tags:**
```
Year 1 Tag: $20M (top 5 average)
Year 2 Tag: $24M (120% of $20M)
Year 3 Tag: $28.8M (144% of $20M) or QB money if higher
```

**Strategic Use:**
- Prevent star players from reaching free agency
- Buy time for long-term deal negotiations
- Expensive but provides certainty
- Often leads to contract extension before tag deadline

### 2. Transition Tag

**Definition:** One-year tender giving team right of first refusal.

**Characteristics:**
- Guaranteed salary: Average of **top 10 salaries** at position (lower than franchise tag)
- Player can negotiate with other teams
- Original team can match any offer
- **No compensation** if team declines to match (unlike franchise tag)

**Comparison to Franchise Tag:**
```
Franchise Tag (Non-Exclusive):
- Top 5 average salary
- Two 1st-round picks if team doesn't match
- Higher cost, more protection

Transition Tag:
- Top 10 average salary
- No compensation if team doesn't match
- Lower cost, less protection
```

**Strategic Use:**
- Cheaper than franchise tag
- Gauges market value for player
- Gives team opportunity to match without high cost
- Rarely used (5-10 times per year across NFL)
- Risk: Could lose player for nothing

### 3. Restricted Free Agent (RFA) Tenders

**Eligibility:** Players with 3 accrued seasons whose contracts have expired

**Tender Levels (2025 Estimates):**

**1st Round Tender (~$7.5M):**
- Compensation: Original team receives 1st-round pick if doesn't match
- Highest cost, best protection

**2nd Round Tender (~$4.8M):**
- Compensation: Original team receives 2nd-round pick if doesn't match
- Medium cost, medium protection

**Original Round Tender (~$3.2M):**
- Compensation: Draft pick from round player was originally drafted
- Lowest cost, variable protection (depends on draft round)

**Right of First Refusal:**
- Team can match any offer sheet
- 5 days to match after offer is signed
- If matched, player stays at offer terms

**Strategic Use:**
- Retain players at below-market cost
- Draft pick compensation deters offer sheets
- Often leads to extensions before offer sheet stage

---

## Minimum Salaries and Rookie Contracts

### 1. Veteran Minimum Salaries (2025)

Minimum salaries increase with years of service (accrued seasons).

**2025 Minimum Salary Scale:**
```
0 years (Rookie):        $840,000
1 year:                  $960,000
2 years:                 $1,045,000
3 years:                 $1,130,000
4-6 years:               $1,240,000
7-9 years:               $1,470,000
10+ years:               $1,630,000
```

**Accrued Season Definition:**
- Player on active roster, injured reserve, or PUP list for at least 6 games
- Practice squad time does NOT count toward accrued season
- Suspended games count if player was on roster

### 2. Veteran Salary Benefit

**Purpose:** Encourages teams to sign veteran players without full cap penalty.

**How It Works:**
- Veteran players with 2+ accrued seasons
- On contracts at veteran minimum salary
- Cap charge is only **2nd-year minimum ($960,000 in 2025)**
- NFL covers difference between cap charge and actual salary

**Example:**
```
10-year veteran signs for minimum: $1,630,000
Cap charge to team: $960,000
NFL covers: $670,000

Team saves: $670,000 in cap space
Veteran earns: Full $1,630,000 salary
```

**Strategic Use:**
- Makes veteran depth players more attractive
- Teams can carry more veterans
- "Prove it" deals for aging stars
- Common for players 30+ years old

### 3. Rookie Contracts

**Rookie Wage Scale:**
- Implemented in 2011 CBA
- Slotted based on draft position
- 4-year contracts (5th year option for 1st rounders)

**Contract Structure:**
- Signing bonus: 100% guaranteed
- Base salaries: Typically guaranteed
- Maximum 25% annual increase

**2025 Rookie Scale Examples (Estimates):**
```
Pick #1 Overall:
- Total Value: ~$40M over 4 years
- Signing Bonus: ~$25M
- 5th Year Option: ~$35M (if exercised)

Pick #32 (Last 1st Round):
- Total Value: ~$15M over 4 years
- Signing Bonus: ~$8M
- 5th Year Option: ~$12M (if exercised)

Pick #100 (3rd Round):
- Total Value: ~$4.5M over 4 years
- Signing Bonus: ~$1M

Pick #200 (6th Round):
- Total Value: ~$4M over 4 years
- Signing Bonus: ~$200K
```

**First-Year Cap Number:**
- Prorated signing bonus amount
- Plus rookie minimum base salary ($840,000)

**Example:**
```
1st overall pick:
Signing Bonus: $25M
Proration: $25M ÷ 4 = $6.25M per year
Year 1 Base: $840,000 (rookie minimum)

Year 1 Cap Hit: $6.25M + $0.84M = $7.09M
```

### 4. Fifth-Year Option (1st Round Picks Only)

**Eligibility:** Players drafted in 1st round

**Timing:** Team must exercise option after player's 3rd season

**Salary Calculation:**
- **Top 10 pick:** Average of top 10 salaries at position
- **Pick 11-32:** Average of 3rd-25th highest salaries at position

**Guaranteed:** Fully guaranteed for injury only until start of 5th year, then becomes fully guaranteed

**Example:**
```
WR drafted 5th overall in 2022
Option exercised after 2024 season for 2026

2026 Option Salary: ~$22M (top 10 WR average)
If injured in 2025 offseason: $22M guaranteed
If healthy at start of 2026: $22M guaranteed
```

**Strategic Use:**
- Extend evaluation period for 1st rounders
- Bridge to long-term extension
- Cost-controlled 5th year
- Common for "good not great" players

---

## Practice Squad

### 1. Practice Squad Size and Eligibility

**2025 Rules:**
- **17 total spots** per team
- **16 standard spots** + **1 International Pathway Program player**

**Eligibility Requirements:**

**Standard Players:**
- No more than 2 accrued seasons
- OR any number of accrued seasons if on practice squad fewer than 9 games in previous seasons
- Maximum **6 veteran players** (2+ accrued seasons) per practice squad

**International Pathway Program:**
- 1 designated spot (in addition to 16)
- Player from outside US
- Doesn't count toward 53-man roster if elevated

### 2. Practice Squad Salaries (2025)

**Standard Weekly Rate:**
```
0-1 accrued seasons: $13,000/week
2+ accrued seasons: $20,000/week (minimum, can be negotiated higher)
```

**Annual Calculation (18-week season):**
```
Rookie Practice Squad: $13,000 × 18 = $234,000/year
Veteran Practice Squad: $20,000 × 18 = $360,000/year
```

**Cap Accounting:**
- Practice squad salaries count against salary cap
- Included in overall team cap calculation
- Different from active roster accounting

### 3. Game Day Elevations

**Rules:**
- Teams can elevate up to **2 practice squad players** per game
- Player reverts to practice squad after game (no roster transaction required)
- Each player can be elevated **3 times per season**
- After 3rd elevation, must be signed to active roster or released

**Salary Treatment:**
- Elevated player earns **active roster prorated minimum** for that week
- Based on player's accrued seasons
- Significantly higher than practice squad rate

**Example:**
```
Rookie practice squad player elevated for 1 game:

Practice Squad Weekly: $13,000
Active Roster Weekly: $840,000 ÷ 17 = ~$49,412

Player earns: $49,412 for that week (not $13,000)
Reverts to practice squad: Back to $13,000/week
```

### 4. Practice Squad Poaching

**Rules:**
- Any team can sign another team's practice squad player to **active 53-man roster**
- Must offer at least 3 weeks of active roster salary
- Original team cannot match
- Player can decline to stay on practice squad

**Protection Period:**
- During season, teams can protect **4 practice squad players** per week
- Protected players cannot be signed by other teams that week
- Protections reset each week

**Strategic Use:**
- Prevents rival teams from poaching key developmental players
- Often used for players learning system
- Quarterback protections common (backup QB development)

---

## Cap Management Strategies

### 1. Front-Loading vs Back-Loading

**Front-Loading:**
- Higher base salaries in early years
- Lower cap hits in later years
- Easier to cut player later without dead money

**Example:**
```
4-year deal, $40M total
Year 1: $15M base
Year 2: $12M base
Year 3: $8M base
Year 4: $5M base

Benefit: Can cut after Year 2 with minimal dead money
```

**Back-Loading:**
- Lower base salaries early
- Higher salaries in later years
- Creates current cap space
- Harder to cut later

**Example:**
```
4-year deal, $40M total
Year 1: $5M base
Year 2: $8M base
Year 3: $12M base
Year 4: $15M base

Benefit: Low cap hits in Years 1-2 for win-now mode
Risk: Years 3-4 create cap pressure
```

### 2. Extending vs Releasing

**Extend Before Contract Ends:**
- Can convert remaining salary to signing bonus
- Spread new signing bonus over new years
- Lowers current cap hit
- Increases future commitment

**Release Player:**
- Immediate cap relief from future base salaries
- Dead money from remaining signing bonus proration
- Opens roster spot
- Lose player's production

**Break-Even Analysis Example:**
```
Player in Year 3 of 5-year deal
Remaining: Years 3, 4, 5
Year 3 Cap Hit: $18M ($5M bonus proration + $13M base)
Years 4-5: $10M bonus proration remaining

Option A: Keep Player
Year 3: $18M cap hit
Years 4-5: ~$15M each year

Option B: Release Player
Year 3: $10M dead money (immediate)
Cap Savings: $8M in Year 3
Years 4-5: $0

Option C: Extend Player
Convert Year 3 base to bonus, extend 2 years
New structure spreads costs over 5 years
Year 3: $10M cap hit
Saves $8M in Year 3, adds commitment through Year 7
```

### 3. "All-In" Strategy

**Description:** Team maximizes current year competitiveness by pushing cap costs to future years.

**Tactics:**
- Restructure multiple contracts
- Add void years to deals
- Trade for expensive players
- Use maximum 2 June 1 designations

**Benefits:**
- Maximizes current roster talent
- Championship window focus
- Can be necessary for Super Bowl run

**Costs:**
- Reduced future flexibility
- Significant future dead money
- Difficult to rebuild roster
- "Cap hell" in future years

**Example Team:**
```
Year 1: Restructure 5 players, create $30M space
Year 2: Restructure again, trade for stars
Year 3: Win Super Bowl
Year 4: $80M in dead money, aging roster, limited space
Years 5-6: Rebuild with minimal cap space
```

### 4. Youth Movement Strategy

**Description:** Build through draft, avoid expensive free agents, maintain cap flexibility.

**Tactics:**
- Heavy draft investment
- Rookie contracts (4-5 years cost-controlled)
- Sign players to 2nd contracts (age 26-28)
- Limited veteran free agent signings
- Trade aging expensive veterans for picks

**Benefits:**
- Sustained cap flexibility
- Young, improving roster
- Longer competitive window
- Can absorb bad contracts

**Costs:**
- Slower path to contention
- Less immediate success
- Development time required
- Requires excellent scouting

**Example Team:**
```
Year 1-2: Trade veterans, accumulate picks
Year 3-4: Draft classes develop, selective FA
Year 5-8: Competitive with young core on rookie deals
Year 8-10: Pay core players, maintain competitiveness
```

### 5. Compensatory Pick Strategy

**Compensatory Picks:**
- Awarded to teams that lose more/better free agents than they sign
- Picks awarded at end of Rounds 3-7
- Cannot be traded (until year of draft)
- Based on contracts lost vs gained

**Strategic Use:**
- Let mid-tier free agents leave
- Avoid signing mid-tier free agents
- Build through draft
- Gain extra picks (up to 4 per year)

**Example:**
```
Team loses:
- WR to $12M/year deal
- CB to $8M/year deal
- LB to $6M/year deal

Team signs:
- Only minimum salary veterans

Result: Gain 3 compensatory picks (Rounds 3-5)
```

---

## Penalties and Violations

### 1. Salary Cap Violations

**Types of Violations:**
- Exceeding salary cap at league year start
- Secret/undisclosed payments to players
- Improper contract structuring
- Circumventing cap rules

**Penalties (At Commissioner's Discretion):**
- **Fines:** Up to **$5 million** per violation
- **Draft pick forfeitures:** Loss of future picks (including 1st rounders)
- **Contract voidances:** Voiding of player contracts
- **Suspension:** Front office personnel suspended
- **Cap reductions:** Future year cap penalties

### 2. Historical Violations

**2012 Dallas Cowboys and Washington Redskins:**
- **Violation:** Excessive spending in 2010 uncapped year
- **Penalty:**
  - Cowboys: $10M cap reduction over 2 years
  - Redskins: $36M cap reduction over 2 years
- **Note:** While technically not a capped year, NFL punished "spirit" violation

**2023 Houston Texans:**
- **Violation:** Salary cap reporting violation
- **Penalty:**
  - Lost 5th-round draft pick in 2023
  - $175,000 fine
- **Issue:** Administrative/paperwork violation

**2015 New Orleans Saints:**
- **Violation:** "Bountygate" (pay-for-performance scheme)
- **Penalty:**
  - Lost 2nd-round picks in 2012 and 2013
  - $500,000 fine
  - Coach suspended for season
  - Note: Primarily conduct violation, but included cap circumvention

### 3. Spending Floor Violations

**89% Rule Enforcement:**
- Teams must spend 89% of cap over 4-year periods
- Measured in **CASH**, not cap accounting
- Violating teams must pay difference to NFLPA
- Money distributed to players on team

**Example:**
```
4-year period cap total: $1B
Team spent: $850M cash
Required: $890M (89%)
Shortfall: $40M

Penalty: Team pays $40M to NFLPA
Distribution: Money goes to players who were on team during period
```

**Enforcement:**
- Rarely violated in practice
- Most teams exceed 89% significantly
- Prevents tanking through payroll suppression

### 4. Contract Circumvention

**Prohibited Activities:**
- Secret payments to players
- Off-books compensation
- Fake jobs for family members
- Non-contract benefits exceeding limits

**Example Violations:**
- Promising future coaching job
- Providing excessive personal services
- Stadium/facility use beyond allowable
- Business investments disguised as salary

**Penalties:**
- Severe draft pick losses
- Major fines
- Potential criminal charges (tax fraud)
- Loss of GM/executive employment

---

## Implementation Considerations

### For "The Owners Sim" Implementation

This section provides guidance on implementing salary cap mechanics in the simulation.

### 1. Core System Requirements

**Essential Components:**
```python
# Minimum viable cap system
- Annual salary cap value (adjustable)
- Player contract tracking (base salary, bonuses)
- Team cap space calculations
- Signing bonus proration
- Dead money calculations
- 53-man roster cap accounting
- Basic contract types (base salary + signing bonus)
```

**Phase 1 Implementation:**
- Fixed annual cap ($279.2M for 2025)
- Base salaries only (no bonuses)
- Simple cap compliance checking
- Rookie minimum salaries by service time
- Basic free agency (cap space determines signings)

**Phase 2 Implementation:**
- Signing bonus proration
- Contract restructuring
- Dead money from releases
- Multiple bonus types
- Top-51 rule (offseason)

**Phase 3 Implementation:**
- Franchise/transition tags
- June 1 designations
- Void years
- Practice squad cap accounting
- Compensatory picks

### 2. Data Structures

**Team Cap Data:**
```python
{
    "team_id": 1,
    "season": 2025,
    "cap_limit": 279200000,
    "top_51_mode": false,  # Toggle for offseason
    "committed_cap": 245000000,
    "available_cap": 34200000,
    "dead_money": 8500000,
    "carryover_from_previous": 5000000
}
```

**Player Contract:**
```python
{
    "player_id": 12345,
    "team_id": 1,
    "contract_years": 4,
    "current_year": 2,
    "base_salaries": [1000000, 5000000, 8000000, 10000000],
    "signing_bonus": 16000000,
    "bonus_proration_annual": 4000000,
    "guaranteed_money": 20000000,
    "is_guaranteed": [true, true, false, false],
    "incentives": {
        "likely_to_earn": 500000,
        "not_likely_to_earn": 1000000
    }
}
```

**Cap Transaction Log:**
```python
{
    "transaction_id": "abc123",
    "team_id": 1,
    "transaction_type": "signing",  # signing, release, restructure, trade
    "player_id": 12345,
    "date": "2025-03-15",
    "cap_impact_current": -8000000,
    "cap_impact_future": {
        "2026": -5000000,
        "2027": -4000000
    },
    "cash_impact": -16000000,
    "dead_money_created": 0
}
```

### 3. Key Calculations

**Available Cap Space:**
```python
def calculate_available_cap(team, roster_mode='regular_season'):
    """
    Calculate team's available salary cap space.

    Args:
        team: Team object
        roster_mode: 'regular_season' (53-man) or 'offseason' (top-51)

    Returns:
        Available cap space (can be negative)
    """
    # Get base cap + carryover
    total_cap = team.base_cap + team.carryover

    # Get contracts to count
    if roster_mode == 'offseason':
        contracts = get_top_51_contracts(team)
    else:
        contracts = get_all_roster_contracts(team)

    # Sum cap hits
    committed = sum(c.current_year_cap_hit for c in contracts)

    # Add dead money
    committed += team.dead_money

    # Add practice squad
    committed += team.practice_squad_cap

    return total_cap - committed
```

**Signing Bonus Proration:**
```python
def calculate_signing_bonus_proration(signing_bonus, contract_years):
    """
    Calculate annual proration of signing bonus.

    Args:
        signing_bonus: Total signing bonus amount
        contract_years: Number of years in contract

    Returns:
        Annual proration amount
    """
    proration_years = min(contract_years, 5)  # Max 5 years
    return signing_bonus / proration_years
```

**Dead Money from Release:**
```python
def calculate_dead_money(player_contract, release_year):
    """
    Calculate dead money cap hit from releasing player.

    Args:
        player_contract: Player's contract object
        release_year: Contract year of release (1-indexed)

    Returns:
        Total dead money cap hit
    """
    # Calculate remaining bonus proration
    years_remaining = player_contract.total_years - release_year + 1
    annual_proration = player_contract.signing_bonus_proration

    dead_money = years_remaining * annual_proration

    # Add any guaranteed base salary
    for year in range(release_year, player_contract.total_years + 1):
        if player_contract.is_guaranteed[year - 1]:
            dead_money += player_contract.base_salaries[year - 1]

    return dead_money
```

**June 1 Dead Money Split:**
```python
def calculate_june_1_dead_money(player_contract, release_year):
    """
    Calculate dead money split over 2 years with June 1 designation.

    Returns:
        Tuple of (current_year_dead_money, next_year_dead_money)
    """
    total_dead_money = calculate_dead_money(player_contract, release_year)
    annual_proration = player_contract.signing_bonus_proration

    # Current year: One year of proration + guaranteed money
    current_year = annual_proration
    for guaranteed_salary in player_contract.guaranteed_base_salaries:
        current_year += guaranteed_salary

    # Next year: Remaining proration
    next_year = total_dead_money - current_year

    return (current_year, next_year)
```

### 4. Simulation Integration Points

**Offseason Phase:**
1. Calculate carryover cap space
2. Process releases/retirements (dead money)
3. Apply franchise/transition tags
4. Free agency (cap space limits signings)
5. Draft rookie contracts
6. Training camp roster construction
7. Final cuts to 53-man roster

**Regular Season Phase:**
1. Weekly roster management (top 53)
2. Practice squad elevations
3. Injury replacements
4. Trade deadline transactions
5. Cap compliance monitoring

**Season End:**
1. Calculate final cap space
2. Determine carryover amount
3. Process compensatory picks
4. Prepare for next season cap

### 5. Difficulty/Realism Settings

**Arcade Mode:**
- Unlimited cap space
- No penalties for overspending
- Simple contract structures

**Simulation Mode:**
- Realistic cap constraints
- All cap rules enforced
- Contract complexity (bonuses, guarantees)
- Penalties for violations

**Dynasty Mode:**
- Multi-year cap management
- Dead money accumulation
- Long-term planning required
- Compensatory pick system

### 6. UI/UX Considerations

**Cap Space Display:**
```
Team Cap Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Salary Cap:        $279,200,000
Committed:         $245,000,000
Dead Money:         $8,500,000
Available:         $25,700,000
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Top-51 Mode: Active (Offseason)
```

**Contract Details View:**
```
Player: Patrick Mahomes
Position: QB
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Year    Base Salary    Bonus    Total Cap Hit
2025    $1,500,000    $44,000,000    $45,500,000
2026    $35,500,000   $44,000,000    $79,500,000
2027    $47,000,000   $44,000,000    $91,000,000
2028    $49,000,000   $0             $49,000,000

Guaranteed: $208M
Dead Money if Cut:
  After 2025: $132M
  After 2026: $88M
  After 2027: $44M
```

**Trade/Release Impact:**
```
Release Patrick Mahomes?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Current Cap Hit: $45,500,000
Dead Money:      $132,000,000
Cap Savings:     -$86,500,000 ❌

This move INCREASES your cap hit by $86.5M

Options:
• Release (Standard)
  - 2025 Dead Money: $132M
• Release (June 1)
  - 2025 Dead Money: $44M
  - 2026 Dead Money: $88M
  - Saves $1.5M in 2025
```

### 7. Testing & Validation

**Unit Tests:**
- Proration calculations
- Dead money calculations
- June 1 designation logic
- Top-51 vs 53-man accounting
- Carryover calculations

**Integration Tests:**
- Full offseason cycle
- Multi-year contract progression
- Trade scenarios with cap implications
- Multiple restructures on same player

**Validation Against Real Data:**
- Compare simulated cap hits to actual NFL contracts
- Verify dead money calculations against real releases
- Test edge cases (void years, option bonuses)

### 8. Common Pitfalls to Avoid

**Cash vs Cap Confusion:**
- Remember: Signing bonus is CASH immediately, but CAP over time
- Don't double-count: Proration replaces cash in cap accounting

**Proration Limits:**
- Max 5 years, not unlimited
- Remaining proration accelerates on release

**Top-51 Rule:**
- Only during offseason
- Affects rookie draft pick cap calculations
- Practice squad doesn't factor into top-51

**Guaranteed Money:**
- Not the same as signing bonus
- Can guarantee base salary separately
- All guarantees become dead money if released

---

## References

- NFL Collective Bargaining Agreement (2020-2030)
- NFL Football Operations Official Documentation
- Over The Cap (overthecap.com) - Industry-standard cap tracking
- Spotrac (spotrac.com) - Contract and cap data
- Pro Football Network - Cap explanations and analysis

---

**Document Version History:**

- v1.0 (October 4, 2025): Initial comprehensive documentation based on 2024-2025 NFL rules and CBA