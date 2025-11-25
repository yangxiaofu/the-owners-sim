# Team Needs Assignment System Design

**Date**: November 2025
**Status**: Design Document (Pre-Implementation)
**Related Files**:
- `src/offseason/team_needs_analyzer.py` - Existing needs analysis engine
- `src/constants/position_abbreviations.py` - Position definitions
- `src/constants/position_hierarchy.py` - Position hierarchy system

---

## Executive Summary

The Team Needs Assignment System provides realistic positional need evaluation for all 32 NFL teams during the offseason. It drives draft selection, free agency priorities, and AI GM decision-making. Teams have different need patterns based on current roster composition, player age, and contract status.

---

## 1. Complete List of NFL Positions for Needs

### 1.1 Offensive Positions (5 position groups)

| Position | Abbreviation | Tier | Description |
|----------|-------------|------|-------------|
| **quarterback** | QB | 1 | Most critical position; typically only 1-2 starters per team |
| **wide_receiver** | WR | 2 | Primary receiving target; teams need multiple WRs |
| **tight_end** | TE | 4 | Receiving option; lower value than premium positions |
| **running_back** | RB | 3 | Ground game and pass-catching; needs depth |
| **fullback** | FB | 4 | Supporting role; rarely drafted early |

### 1.2 Offensive Line Positions (5 position groups)

| Position | Abbreviation | Tier | Description |
|----------|-------------|------|-------------|
| **left_tackle** | LT | 1 | Protects QB's blind side; premium position |
| **right_tackle** | RT | 1 | Pass protection; valuable but less critical than LT |
| **center** | C | 2 | Snap quality and interior pass protection |
| **left_guard** | LG | 3 | Interior line; important but less valued than tackles |
| **right_guard** | RG | 3 | Interior line; important but less valued than tackles |

### 1.3 Defensive Line Positions (3 position groups)

| Position | Abbreviation | Tier | Description |
|----------|-------------|------|-------------|
| **defensive_end** | DE | 1 | Pass rush and edge defense; premium position |
| **defensive_tackle** | DT | 4 | Interior rush and run defense |
| **nose_tackle** | NT | 4 | 3-4 alignment; specific to scheme |

### 1.4 Linebacker Positions (5 position groups)

| Position | Abbreviation | Tier | Description |
|----------|-------------|------|-------------|
| **linebacker** | LB | 3 | Generic linebacker; used as fallback |
| **mike_linebacker** | MIKE | 3 | Middle linebacker; run defense |
| **outside_linebacker** | OLB | 3 | Edge linebacker; pass rush |
| **inside_linebacker** | ILB | 3 | Interior linebacker; coverage |
| **weak_side_linebacker** | WIL | 3 | Versatile linebacker |

### 1.5 Secondary/Defensive Back Positions (5 position groups)

| Position | Abbreviation | Tier | Description |
|----------|-------------|------|-------------|
| **cornerback** | CB | 2 | Man coverage; critical for modern NFL |
| **free_safety** | FS | 2 | Centerfield coverage; value-added role |
| **strong_safety** | SS | 3 | Box coverage; scheme-dependent |
| **safety** | S | 2 | Generic safety; used as fallback |
| **nickel_cornerback** | NCB | 3 | Sub-package DB; situational player |

### 1.6 Special Teams Positions (5 position groups)

| Position | Abbreviation | Tier | Description |
|----------|-------------|------|-------------|
| **kicker** | K | 4 | Field goals and extra points |
| **punter** | P | 4 | Punting; situational specialist |
| **long_snapper** | LS | 4 | Snapping; critical but few players |
| **kick_returner** | KR | 4 | Return specialist; depth player |
| **punt_returner** | PR | 4 | Return specialist; depth player |

### Summary by Tier

| Tier | Urgency Score | Positions | Example Starter Threshold |
|------|-------|-----------|-----------|
| **Tier 1 (Premium)** | Higher weight | QB, DE, LT, RT | 75+ overall |
| **Tier 2 (High)** | Significant weight | WR, CB, C, FS, S | 72+ overall |
| **Tier 3 (Standard)** | Normal weight | RB, LB, LG, RG, SS | 70+ overall |
| **Tier 4 (Lower)** | Lower weight | TE, DT, K, P, LS, FB | 68+ overall |

---

## 2. Realistic Needs Distribution

### 2.1 Fact Checks from NFL Reality

1. **Not all teams need QB**: Only 5-8 teams in any draft class need QBs
2. **DE/CB are always needed**: Nearly every team can use better edge rush or coverage
3. **OL depth is critical**: Even good teams rotate 8-10 OL on roster
4. **Position clusters**: Teams often have multiple needs in same group (multiple WRs, multiple DBs)
5. **Age impacts urgency**: Aging starters elevate position need urgency
6. **Contract timing**: Teams losing starters to free agency create CRITICAL needs

### 2.2 Five Realistic Needs Templates

#### **Template 1: Contending Team (Good Roster)**

Scenario: Defending playoff team with solid roster but aging defense

```json
{
  "team_id": 1,
  "team_name": "Example Contenders",
  "template_name": "Contenders",
  "description": "Good team in win-now mode, needs depth and edge talent",
  "needs": [
    {
      "position": "defensive_end",
      "urgency": "MEDIUM",
      "urgency_score": 3,
      "reason": "Starter aging (34 yo), need future replacement"
    },
    {
      "position": "cornerback",
      "urgency": "MEDIUM",
      "urgency_score": 3,
      "reason": "Secondary depth weakness"
    },
    {
      "position": "safety",
      "urgency": "LOW",
      "urgency_score": 2,
      "reason": "Adequate depth, solid starter"
    },
    {
      "position": "offensive_line",
      "urgency": "LOW",
      "urgency_score": 2,
      "reason": "Multiple OL starters, need depth rotations"
    },
    {
      "position": "running_back",
      "urgency": "LOW",
      "urgency_score": 2,
      "reason": "Starter solid but no quality backup"
    }
  ]
}
```

#### **Template 2: Rebuilding Team (Young Core)**

Scenario: Team in rebuild with young QB, needs foundational pieces

```json
{
  "team_id": 2,
  "team_name": "Example Rebuilding",
  "template_name": "Rebuilding",
  "description": "Young team with QB, building around cornerstone positions",
  "needs": [
    {
      "position": "left_tackle",
      "urgency": "CRITICAL",
      "urgency_score": 5,
      "reason": "Young QB needs protection, current starter (70 OVR)"
    },
    {
      "position": "wide_receiver",
      "urgency": "HIGH",
      "urgency_score": 4,
      "reason": "No elite WR option, need multiple weapons"
    },
    {
      "position": "cornerback",
      "urgency": "HIGH",
      "urgency_score": 4,
      "reason": "Secondary struggling, need shutdown corner"
    },
    {
      "position": "defensive_end",
      "urgency": "MEDIUM",
      "urgency_score": 3,
      "reason": "Defense needs starter-quality pass rush"
    },
    {
      "position": "center",
      "urgency": "MEDIUM",
      "urgency_score": 3,
      "reason": "Interior OL depth and stability"
    }
  ]
}
```

#### **Template 3: Missing QB (Draft Year)**

Scenario: Team needs franchise QB in draft

```json
{
  "team_id": 3,
  "team_name": "Example QB Hunt",
  "template_name": "QB Draft Class",
  "description": "Top priority is franchise QB, fill supporting pieces",
  "needs": [
    {
      "position": "quarterback",
      "urgency": "CRITICAL",
      "urgency_score": 5,
      "reason": "No starter, transitional veteran in place"
    },
    {
      "position": "wide_receiver",
      "urgency": "CRITICAL",
      "urgency_score": 5,
      "reason": "QB needs weapons for success"
    },
    {
      "position": "left_tackle",
      "urgency": "HIGH",
      "urgency_score": 4,
      "reason": "QB protection critical"
    },
    {
      "position": "tight_end",
      "urgency": "HIGH",
      "urgency_score": 4,
      "reason": "Rookie QB targets, safety valve"
    },
    {
      "position": "defensive_end",
      "urgency": "MEDIUM",
      "urgency_score": 3,
      "reason": "Defense needs help but QB is first priority"
    }
  ]
}
```

#### **Template 4: Losing Star (Free Agency Loss)**

Scenario: Team lost major star to free agency, filling void in draft

```json
{
  "team_id": 4,
  "team_name": "Example Free Agency Loss",
  "template_name": "Star Loss",
  "description": "Lost elite player to free agency, need immediate replacement",
  "needs": [
    {
      "position": "cornerback",
      "urgency": "CRITICAL",
      "urgency_score": 5,
      "reason": "Lost Pro-Bowl CB to free agency, secondary exposed"
    },
    {
      "position": "safety",
      "urgency": "HIGH",
      "urgency_score": 4,
      "reason": "Backup safety promotion, need coverage help"
    },
    {
      "position": "linebacker",
      "urgency": "MEDIUM",
      "urgency_score": 3,
      "reason": "Defense reshuffling around CB loss"
    },
    {
      "position": "wide_receiver",
      "urgency": "LOW",
      "urgency_score": 2,
      "reason": "Offense stable, focus on defense"
    },
    {
      "position": "offensive_line",
      "urgency": "LOW",
      "urgency_score": 2,
      "reason": "OL depth is adequate"
    }
  ]
}
```

#### **Template 5: Balanced Team (No Glaring Holes)**

Scenario: Solid roster, need incremental improvements across board

```json
{
  "team_id": 5,
  "team_name": "Example Balanced",
  "template_name": "Balanced",
  "description": "No critical needs, want to improve depth at multiple positions",
  "needs": [
    {
      "position": "wide_receiver",
      "urgency": "MEDIUM",
      "urgency_score": 3,
      "reason": "Starter solid but nice to add depth"
    },
    {
      "position": "defensive_end",
      "urgency": "MEDIUM",
      "urgency_score": 3,
      "reason": "Could upgrade pass rush production"
    },
    {
      "position": "offensive_line",
      "urgency": "MEDIUM",
      "urgency_score": 3,
      "reason": "Multiple OL approaching free agency"
    },
    {
      "position": "cornerback",
      "urgency": "LOW",
      "urgency_score": 2,
      "reason": "Secondary solid, adequate depth"
    },
    {
      "position": "running_back",
      "urgency": "LOW",
      "urgency_score": 2,
      "reason": "RB committee working well"
    }
  ]
}
```

---

## 3. Assignment Algorithm for 32 Teams

### 3.1 Algorithm Overview

The needs assignment is **dynamic and roster-driven**, not template-based. It evaluates each team's actual roster state:

```
For each team (1-32):
  1. Get full depth chart (all positions, depth order)
  2. For each important position (16 positions across tiers):
    a. Identify starter (depth_order = 1)
    b. Count backups (depth_order > 1 and < 99)
    c. Get expiring contracts (next 2 seasons)
    d. Calculate urgency score based on:
       - Starter overall rating vs threshold
       - Backup quality and count
       - Starter contract expiration
       - Position tier importance
  3. Sort positions by urgency (CRITICAL → NONE)
  4. Return top 5 needs for draft/free agency focus
```

### 3.2 Urgency Calculation Logic

Implemented in `TeamNeedsAnalyzer._calculate_urgency()`:

```python
CRITICAL (5):
  - No starter at position
  - Starter overall < (tier_threshold - 5) [e.g., QB < 70 overall]
  - Starter leaving AND no adequate replacement

HIGH (4):
  - Starter overall < tier_threshold [e.g., QB < 75 overall]
  - Starter leaving (contract expiring)
  - No backup depth (0 backups for premium position)

MEDIUM (3):
  - Starter decent but weak backup depth
  - Premium position with insufficient depth (< 2 backups)
  - Starter 75-80 overall with aging backups

LOW (2):
  - Starter good (80-85 overall), adequate depth
  - Position solid, optional upgrade opportunity

NONE (1):
  - Starter great (85+ overall), good depth
  - Position well-staffed, no foreseeable need
```

### 3.3 Position Tier Thresholds

Directly from `TeamNeedsAnalyzer.STARTER_THRESHOLDS`:

| Tier | Positions | Starter Threshold |
|------|-----------|-------------------|
| 1 | QB, DE, LT, RT | 75+ overall |
| 2 | WR, CB, C | 72+ overall |
| 3 | RB, LB, LG, RG, S, SS | 70+ overall |
| 4 | TE, DT, K, P, LS, FB | 68+ overall |

### 3.4 Assignment Example (3 Sample Teams)

#### Team 1: Kansas City Chiefs (Contenders)

Current roster state:
- QB: Patrick Mahomes (88 OVR, contract through 2027)
- DE: George Karl (85 OVR, 35 years old)
- WR: Travis Kelce (87 OVR, aging TE, contract expiring 2025)
- CB: L'Jarius Sneed (82 OVR, contract through 2027)

Needs Analysis:
```
Position              Starter    Backups   Urgency  Reason
===================================================================
defensive_end        85 OVR     1 backup  MEDIUM   Aging starter, need succession plan
wide_receiver         82 OVR     2 backups MEDIUM   Need skill position depth
cornerback            82 OVR     3 backups LOW      Strong secondary, adequate depth
tight_end             87 OVR     1 backup  LOW      Kelce solid, need backup for aging
left_tackle           80 OVR     1 backup  LOW      Starter adequate, some depth
running_back          80 OVR     2 backups LOW      Committee working, some depth
```

**Top 5 Needs**:
1. Defensive End (MEDIUM)
2. Wide Receiver (MEDIUM)
3. Cornerback (LOW)
4. Tight End (LOW)
5. Left Tackle (LOW)

---

#### Team 2: Chicago Bears (Rebuilding - Young QB)

Current roster state:
- QB: Caleb Williams (76 OVR, contract 2024-2027 rookie deal)
- LT: Denzell Wright (68 OVR, aging tackle, contract expiring 2025)
- WR: None elite (highest 72 OVR)
- DE: 0 starters
- CB: Limited depth

Needs Analysis:
```
Position              Starter    Backups   Urgency  Reason
===================================================================
left_tackle          68 OVR     0 backups CRITICAL No quality starter for young QB
wide_receiver         72 OVR     1 backup  CRITICAL Young QB needs weapons
defensive_end        65 OVR     0 backups CRITICAL No pass rush, defense exposed
cornerback            70 OVR     1 backup  HIGH     Secondary weakness
center                71 OVR     1 backup  MEDIUM   Interior OL needs help
```

**Top 5 Needs**:
1. Left Tackle (CRITICAL)
2. Wide Receiver (CRITICAL)
3. Defensive End (CRITICAL)
4. Cornerback (HIGH)
5. Center (MEDIUM)

---

#### Team 3: San Francisco 49ers (Balanced Contenders)

Current roster state:
- QB: Brock Purdy (87 OVR, contract through 2027)
- RB: Elijah Mitchell (83 OVR), Jeff Richter (81 OVR)
- WR: Brandon Aiyuk (86 OVR), multiple depth pieces
- DE: Multiple 82+ OVR starters
- CB: Deommodore Lenoir (80 OVR), multiple depth

Needs Analysis:
```
Position              Starter    Backups   Urgency  Reason
===================================================================
linebacker           78 OVR     2 backups MEDIUM   Solid backups, starter average
safety                81 OVR     2 backups LOW      Coverage adequate, good depth
wide_receiver         86 OVR     3 backups LOW      Elite WR, excellent depth
defensive_end        84 OVR     2 backups LOW      Strong pass rush, depth there
offensive_line       82 OVR     3+ backups LOW     Excellent interior line depth
```

**Top 5 Needs**:
1. Linebacker (MEDIUM)
2. Safety (LOW)
3. Tight End (LOW)
4. Cornerback (LOW)
5. Defensive Tackle (LOW)

---

### 3.5 Implementation Pseudocode

```python
def assign_needs_to_all_teams(season_year: int) -> Dict[int, List[Dict]]:
    """
    Assign needs to all 32 NFL teams for a season.

    Returns:
        {
            1: [need1_dict, need2_dict, ...],
            2: [need1_dict, need2_dict, ...],
            ...
            32: [need1_dict, need2_dict, ...]
        }
    """
    analyzer = TeamNeedsAnalyzer(database_path, dynasty_id)
    all_team_needs = {}

    for team_id in range(1, 33):
        # Dynamic analysis for this team
        team_needs = analyzer.analyze_team_needs(
            team_id=team_id,
            season=season_year,
            include_future_contracts=True
        )

        # Store top 5 needs for this team
        all_team_needs[team_id] = analyzer.get_top_needs(
            team_id=team_id,
            season=season_year,
            limit=5
        )

    return all_team_needs
```

---

## 4. Output Formats

### 4.1 Single Team Needs Display

#### Raw JSON Format (Database)

```json
{
  "team_id": 22,
  "team_name": "Detroit Lions",
  "season_year": 2024,
  "needs": [
    {
      "position": "wide_receiver",
      "urgency": "CRITICAL",
      "urgency_score": 5,
      "starter_overall": 68,
      "depth_count": 1,
      "avg_depth_overall": 64,
      "starter_leaving": false,
      "reason": "Starter well below standard (68 overall)"
    },
    {
      "position": "cornerback",
      "urgency": "HIGH",
      "urgency_score": 4,
      "starter_overall": 72,
      "depth_count": 0,
      "avg_depth_overall": 0,
      "starter_leaving": false,
      "reason": "No backup depth"
    },
    {
      "position": "offensive_line",
      "urgency": "MEDIUM",
      "urgency_score": 3,
      "starter_overall": 76,
      "depth_count": 2,
      "avg_depth_overall": 68,
      "starter_leaving": false,
      "reason": "Weak depth behind starter"
    },
    {
      "position": "defensive_end",
      "urgency": "LOW",
      "urgency_score": 2,
      "starter_overall": 80,
      "depth_count": 2,
      "avg_depth_overall": 75,
      "starter_leaving": false,
      "reason": "Starter solid, could upgrade depth"
    },
    {
      "position": "running_back",
      "urgency": "LOW",
      "urgency_score": 2,
      "starter_overall": 81,
      "depth_count": 3,
      "avg_depth_overall": 73,
      "starter_leaving": false,
      "reason": "Starter solid, could upgrade depth"
    }
  ]
}
```

#### CLI Display Format (Interactive)

```
═══════════════════════════════════════════════════════════════
        Detroit Lions - 2024 Draft Priorities
═══════════════════════════════════════════════════════════════

📍 CRITICAL NEEDS (Address in Round 1):
  ⚠️  Wide Receiver
      Starter: 68 OVR (Sub-standard)
      Backups: 1 (avg 64 OVR)
      Action: Young WR weapon for offense

📍 HIGH PRIORITY (Address by Round 2-3):
  ⬆️  Cornerback
      Starter: 72 OVR (Below standard)
      Backups: None!
      Action: Shutdown corner urgently needed

📍 MEDIUM PRIORITY (Address in Round 4-5):
  ➡️  Offensive Line
      Starter: 76 OVR (Adequate)
      Backups: 2 (avg 68 OVR)
      Action: Improve depth behind starter

📍 LOW PRIORITY (Bonus/Depth):
  ◈ Defensive End (80 OVR starter, adequate depth)
  ◈ Running Back (81 OVR starter, solid depth)

═══════════════════════════════════════════════════════════════
```

#### Draft Board UI Format

```
DETROIT LIONS DRAFT BOARD

Tier 1 (CRITICAL):
  [WR] - CRITICAL NEED - Starter 68 OVR
        • Positions with this need: 5
        • Top prospect: DeVonta Smith (WR, 92 OVR)
        • Value: Extremely High

Tier 2 (HIGH):
  [CB] - HIGH NEED - No backups!
        • Positions with this need: 12
        • Top prospect: Malachi Starks (CB, 88 OVR)
        • Value: Very High

Tier 3 (MEDIUM):
  [OL] - MEDIUM NEED - Weak depth
        • Positions with this need: 18
        • Top prospect: Olu Fashanu (LT, 87 OVR)
        • Value: High

[Show all available prospects sorted by value for this team]
```

---

## 5. Matching Drafted Position to Team Need

### 5.1 Matching Algorithm

When a team makes a draft pick, the system evaluates the match:

```python
def evaluate_draft_pick_fit(
    team_id: int,
    prospect: Dict[str, Any],  # {position, overall, ...}
    team_needs: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Evaluate how well a prospect matches team's needs.

    Returns:
        {
            'position_match': 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'NO_MATCH',
            'match_score': 0-100,
            'urgency': int,  # From team_needs
            'reasoning': str,
            'highlight': bool  # Display prominently if True
        }
    """
    prospect_position = prospect['position']
    prospect_overall = prospect['overall']

    # Find matching need
    matching_need = None
    for need in team_needs:
        if positions_match(prospect_position, need['position']):
            matching_need = need
            break

    if not matching_need:
        return {
            'position_match': 'NO_MATCH',
            'match_score': 0,
            'urgency': 0,
            'reasoning': f"{prospect['position']} not in top 5 needs",
            'highlight': False
        }

    # Calculate match score
    urgency_score = matching_need['urgency_score']
    prospect_quality = min(prospect_overall - 75, 20)  # Bonus for elite prospect

    match_score = min(100, urgency_score * 20 + prospect_quality)

    return {
        'position_match': matching_need['urgency'].name,
        'match_score': match_score,
        'urgency': urgency_score,
        'reasoning': matching_need['reason'],
        'highlight': urgency_score >= 4  # CRITICAL or HIGH
    }
```

### 5.2 Position Matching Logic

**Exact Position Match** (100% value):
```
Prospect position exactly matches need position
  QB prospect → QB need ✓
  WR prospect → WR need ✓
```

**Hierarchy Match** (80% value):
```
Prospect position is child of need position
  WR prospect → Receiver need (generic)
  LG prospect → Guard need (generic)
  CB prospect → Cornerback need (child of DB)
```

**Group Match** (60% value):
```
Prospect position is in same group as need
  LT prospect → RG need (both offensive_line)
  DE prospect → DT need (both defensive_line)
  ILB prospect → OLB need (both linebacker)
```

**No Match** (0% value):
```
Prospect position unrelated to need
  WR prospect → QB need ✗
  QB prospect → DE need ✗
```

---

### 5.3 Pick Evaluation UI Display

#### **Excellent Match** (CRITICAL Need + Elite Prospect)

```
═══════════════════════════════════════════════════════════════
PICK EVALUATION: Detroit Lions - Pick #6
═══════════════════════════════════════════════════════════════

🎯 EXCELLENT MATCH - HIGHLIGHTING!

PROSPECT:
  Name: DeVonta Smith
  Position: Wide Receiver (WR)
  Overall: 92 OVR
  Projected Range: Picks 2-8

TEAM NEED:
  Position: Wide Receiver
  Urgency: CRITICAL (5/5)
  Starter: 68 OVR (Sub-standard!)
  Backups: 1 (avg 64 OVR)
  Reason: "Starter well below standard"

MATCH ANALYSIS:
  ✓ Position Match: EXACT
  ✓ Need Urgency: CRITICAL (highest level)
  ✓ Prospect Quality: ELITE (92 OVR, top 10 talent)
  ✓ Tier Alignment: Tier 2 need with Tier 1 prospect

RECOMMENDATION:
  🟢 STRONG PICK - Addresses critical need with elite talent
  Expected Value: 92/100
  Draft Score: +15 (fills urgent need)
  Overall Assessment: Outstanding selection

═══════════════════════════════════════════════════════════════
```

#### **Good Match** (HIGH Need + Good Prospect)

```
═══════════════════════════════════════════════════════════════
PICK EVALUATION: Detroit Lions - Pick #42
═══════════════════════════════════════════════════════════════

✓ GOOD MATCH

PROSPECT:
  Name: Malachi Starks
  Position: Cornerback (CB)
  Overall: 88 OVR
  Projected Range: Picks 28-40

TEAM NEED:
  Position: Cornerback
  Urgency: HIGH (4/5)
  Starter: 72 OVR (Below standard)
  Backups: 0 (CRITICAL!)
  Reason: "No backup depth"

MATCH ANALYSIS:
  ✓ Position Match: EXACT
  ✓ Need Urgency: HIGH (second-highest level)
  ✓ Prospect Quality: VERY GOOD (88 OVR, solid Day 1 talent)
  ✓ Tier Alignment: Tier 2 need with strong prospect

RECOMMENDATION:
  🟡 SOLID PICK - Fills high-priority need with quality prospect
  Expected Value: 85/100
  Draft Score: +8 (fills HIGH need)
  Overall Assessment: Good value and need fit

═══════════════════════════════════════════════════════════════
```

#### **Weak Match** (LOW Need + Any Prospect)

```
═══════════════════════════════════════════════════════════════
PICK EVALUATION: Detroit Lions - Pick #58
═══════════════════════════════════════════════════════════════

⚠️  WEAK MATCH - Consider alternatives?

PROSPECT:
  Name: Gibbs (RB)
  Position: Running Back (RB)
  Overall: 82 OVR
  Projected Range: Picks 25-35

TEAM NEED STATUS:
  Position: Running Back
  Urgency: LOW (2/5)
  Starter: 81 OVR (Solid)
  Backups: 3 (avg 73 OVR)
  Reason: "Starter solid, could upgrade depth"

MATCH ANALYSIS:
  ✓ Position Match: EXACT
  ✗ Need Urgency: LOW (lowest level, 5 higher-priority needs)
  ✓ Prospect Quality: GOOD (82 OVR)
  ✗ Tier Alignment: Tier 3 prospect, addressing Tier 3 need

RECOMMENDATION:
  🔴 WEAK PICK - Lower priority need, many better options
  Expected Value: 45/100
  Draft Score: +3 (fills LOW need only)
  Alternative: Consider CRITICAL/HIGH needs in this range

  Better options available:
    • Interior OL (MEDIUM need, RB depth adequate)
    • Defensive End (MEDIUM need, elite prospect)
    • Tight End backup (MEDIUM need)

═══════════════════════════════════════════════════════════════
```

#### **No Match** (Prospect Position Not in Top 5 Needs)

```
═══════════════════════════════════════════════════════════════
PICK EVALUATION: Detroit Lions - Pick #72
═══════════════════════════════════════════════════════════════

✗ NO MATCH - Off-board for this team

PROSPECT:
  Name: Jones (Punter)
  Position: Punter (P)
  Overall: 79 OVR
  Projected Range: Picks 100-120

TEAM NEEDS ANALYSIS:
  Top 5 Needs (No Punter):
    1. Wide Receiver (CRITICAL)
    2. Cornerback (HIGH)
    3. Offensive Line (MEDIUM)
    4. Defensive End (LOW)
    5. Running Back (LOW)

MATCH ANALYSIS:
  ✗ Position Match: NO MATCH
  ✗ Need Urgency: NONE (0/5)
  ✓ Prospect Quality: GOOD (79 OVR)
  ✗ Tier Alignment: Tier 4 position, no priority need

RECOMMENDATION:
  ❌ POOR PICK - Not addressing team needs
  Expected Value: 20/100
  Draft Score: -5 (fills non-priority position)
  Alternative: Current starter adequate for 2+ seasons

  Better options available:
    • Offensive Line depth (MEDIUM need)
    • Tight End development (MEDIUM need)
    • Any CB/WR prospect available

═══════════════════════════════════════════════════════════════
```

---

### 5.4 Pick Highlighting System

**Highlight Rules**:

| Scenario | Highlight Color | Reasoning |
|----------|-----------------|-----------|
| CRITICAL need + Elite prospect (85+ OVR) | 🟢 Green | Perfect fit |
| HIGH need + Good prospect (80+ OVR) | 🟡 Yellow | Solid fit |
| MEDIUM need + decent prospect | ◈ Neutral | Reasonable |
| LOW need + any prospect | 🔴 Red | Question fit |
| NO MATCH | ❌ Red | Off-board |

**Visual Indicators**:

```
Draft Board Display:

🟢 Pick 6: DeVonta Smith (WR, 92 OVR) - CRITICAL MATCH
   └─ Addresses WR CRITICAL need

🟡 Pick 42: Malachi Starks (CB, 88 OVR) - HIGH MATCH
   └─ Addresses CB HIGH need

◈ Pick 58: Gibbs (RB, 82 OVR) - LOW MATCH
   └─ Addresses RB LOW need (better options available)

🔴 Pick 72: Jones (P, 79 OVR) - NO MATCH
   └─ Off-board (P not in top 5 needs)
```

---

## 6. Integration Points

### 6.1 How Needs Feed Draft Decisions

```
Draft Manager Flow:
  1. Get all team needs via TeamNeedsAnalyzer.analyze_team_needs()
  2. For each prospect evaluation:
     a. Check if prospect position matches any CRITICAL/HIGH needs
     b. Apply urgency bonus (+15 CRITICAL, +8 HIGH, +3 MEDIUM)
     c. Evaluate prospect quality and age
     d. Calculate final value score
  3. AI selects highest-value prospect that fits needs
  4. User sees pick evaluation with need highlighting
```

### 6.2 How Needs Feed Free Agency

```
Free Agency Manager Flow:
  1. Get team needs at start of free agency
  2. For each free agent evaluation:
     a. Check if FA position matches any HIGH/CRITICAL needs
     b. Evaluate contract cost vs cap space
     c. Calculate fit bonus if need match exists
     d. Apply GM personality modifiers
  3. AI team prioritizes signings in HIGH/CRITICAL positions
  4. User can see recommended targets by need
```

### 6.3 How Needs Feed AI Trades

```
Trade Proposal Flow:
  1. Get team needs and assets
  2. Identify needs that could be filled via trade
  3. Evaluate trading current assets for need positions
  4. Use need urgency to determine trade value thresholds
  5. AI more aggressive trading for CRITICAL/HIGH needs
```

---

## 7. Example Data Structures

### 7.1 Team Needs Object

```python
@dataclass
class PositionalNeed:
    position: str  # e.g., "wide_receiver"
    urgency: NeedUrgency  # enum: CRITICAL, HIGH, MEDIUM, LOW, NONE
    urgency_score: int  # 5, 4, 3, 2, 1
    starter_overall: int  # Overall rating of current starter (0 if none)
    depth_count: int  # Number of backup players
    avg_depth_overall: float  # Average overall of backups
    starter_leaving: bool  # Contract expires next season
    reason: str  # Human-readable explanation
    tier: int  # 1-4, lower = more important

@dataclass
class TeamNeedsProfile:
    team_id: int
    team_name: str
    season_year: int
    all_needs: List[PositionalNeed]  # All positions analyzed
    top_5_needs: List[PositionalNeed]  # Prioritized for draft
    critical_count: int  # Number of CRITICAL needs
    high_count: int  # Number of HIGH needs

    def get_needs_by_urgency(self, urgency: NeedUrgency) -> List[PositionalNeed]:
        return [n for n in self.all_needs if n.urgency == urgency]
```

### 7.2 Draft Pick Evaluation Object

```python
@dataclass
class DraftPickEvaluation:
    team_id: int
    pick_number: int
    prospect: Dict[str, Any]
    position_match: str  # 'EXACT', 'HIERARCHY', 'GROUP', 'NO_MATCH'
    match_score: int  # 0-100
    urgency_level: NeedUrgency  # From matching need
    reasoning: str
    highlight: bool  # Should display prominently
    recommendation: str  # E.g., "STRONG PICK", "WEAK PICK"
    expected_value: int  # 0-100
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

```python
def test_team_needs_analyzer_critical_need():
    """Test that missing starter creates CRITICAL need."""
    needs = analyzer.analyze_team_needs(team_id=1, season=2024)
    assert needs[0]['urgency'] == NeedUrgency.CRITICAL

def test_team_needs_analyzer_no_backup():
    """Test that premium position with no backup = HIGH need."""
    needs = analyzer.analyze_team_needs(team_id=2, season=2024)
    cb_need = next(n for n in needs if n['position'] == 'cornerback')
    assert cb_need['urgency'] == NeedUrgency.HIGH
    assert cb_need['depth_count'] == 0

def test_draft_pick_matching_exact():
    """Test exact position match (WR pick → WR need)."""
    result = evaluate_draft_pick_fit(
        team_id=1,
        prospect={'position': 'wide_receiver', 'overall': 92},
        team_needs=[{'position': 'wide_receiver', 'urgency_score': 5}]
    )
    assert result['position_match'] == 'EXACT'
    assert result['match_score'] > 80

def test_draft_pick_matching_hierarchy():
    """Test hierarchy match (LG pick → Guard need)."""
    result = evaluate_draft_pick_fit(
        team_id=1,
        prospect={'position': 'left_guard', 'overall': 85},
        team_needs=[{'position': 'guard', 'urgency_score': 3}]
    )
    assert result['position_match'] == 'HIERARCHY'

def test_draft_pick_no_match():
    """Test no match (Punter pick when not in top 5 needs)."""
    result = evaluate_draft_pick_fit(
        team_id=1,
        prospect={'position': 'punter', 'overall': 79},
        team_needs=[{...}]  # No punter in top 5
    )
    assert result['position_match'] == 'NO_MATCH'
    assert not result['highlight']
```

### 8.2 Integration Tests

```python
def test_all_32_teams_have_needs():
    """Verify all 32 teams get assigned realistic needs."""
    all_needs = assign_needs_to_all_teams(season_year=2024)
    assert len(all_needs) == 32

    for team_id in range(1, 33):
        team_needs = all_needs[team_id]
        assert len(team_needs) > 0
        assert len(team_needs) <= 5

def test_qb_rarely_critical_need():
    """Verify only few teams have QB as critical need."""
    all_needs = assign_needs_to_all_teams(season_year=2024)
    qb_critical_count = sum(
        1 for needs in all_needs.values()
        if any(n['position'] == 'quarterback' and n['urgency_score'] == 5 for n in needs)
    )
    assert qb_critical_count <= 8  # Few teams need QB

def test_de_cb_always_valued():
    """Verify DE and CB are high-value needs for most teams."""
    all_needs = assign_needs_to_all_teams(season_year=2024)
    de_high_count = sum(
        1 for needs in all_needs.values()
        if any(n['position'] == 'defensive_end' and n['urgency_score'] >= 3 for n in needs)
    )
    cb_high_count = sum(
        1 for needs in all_needs.values()
        if any(n['position'] == 'cornerback' and n['urgency_score'] >= 3 for n in needs)
    )
    assert de_high_count >= 25  # At least 75% of teams
    assert cb_high_count >= 25
```

---

## 9. Summary

The Team Needs Assignment System provides:

1. **Dynamic Analysis**: Real roster-driven need evaluation, not templates
2. **Realistic Distribution**: QB needs rare, DE/CB always valued
3. **Clear Hierarchy**: CRITICAL → HIGH → MEDIUM → LOW urgency levels
4. **Position Matching**: Exact, hierarchy, group, and no-match detection
5. **Visual Feedback**: Color-coded highlighting and detailed UI displays
6. **AI Integration**: Drives draft, free agency, and trade decisions
7. **Extensible Design**: Easy to add new positions or modify thresholds

All analysis is built on the existing `TeamNeedsAnalyzer` class, requiring no breaking changes to current architecture.

---

## Appendix: Configuration Constants

All thresholds defined in `src/offseason/team_needs_analyzer.py`:

```python
# Position tier classifications
TIER_1_POSITIONS = ['quarterback', 'defensive_end', 'left_tackle', 'right_tackle']
TIER_2_POSITIONS = ['wide_receiver', 'cornerback', 'center']
TIER_3_POSITIONS = ['running_back', 'linebacker', 'safety', 'left_guard', 'right_guard']
TIER_4_POSITIONS = ['tight_end', 'defensive_tackle']

# Starter rating thresholds by tier
STARTER_THRESHOLDS = {
    1: 75,  # Premium positions
    2: 72,  # Important positions
    3: 70,  # Standard positions
    4: 68   # Lower value positions
}

# Urgency enumeration
class NeedUrgency(Enum):
    CRITICAL = 5  # No starter or starter < 70 overall
    HIGH = 4      # Starter 70-75 overall or no backup
    MEDIUM = 3    # Starter 75-80 overall or weak depth
    LOW = 2       # Starter 80-85 overall, adequate depth
    NONE = 1      # Starter 85+ overall, good depth
```
