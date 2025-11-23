# Team Needs Assignment System - Quick Reference

**Status**: Design Reference Document
**Related**: `TEAM_NEEDS_ASSIGNMENT_SYSTEM.md` (full design)

---

## 1. Position Quick Reference

### All Positions by Tier

```
TIER 1 (Premium - 75+ overall starter needed):
  ✓ QB - Quarterback (WR: QB)
  ✓ DE - Defensive End (Parent: DL)
  ✓ LT - Left Tackle (Parent: OL)
  ✓ RT - Right Tackle (Parent: OL)

TIER 2 (High Value - 72+ overall starter needed):
  ✓ WR - Wide Receiver
  ✓ CB - Cornerback (Parent: DB)
  ✓ C - Center (Parent: OL)
  ✓ FS - Free Safety (Parent: S, DB)
  ✓ S - Safety (Parent: DB)

TIER 3 (Standard - 70+ overall starter needed):
  ✓ RB - Running Back
  ✓ LB - Linebacker (includes MIKE, OLB, ILB, WIL)
  ✓ LG - Left Guard (Parent: OL)
  ✓ RG - Right Guard (Parent: OL)
  ✓ SS - Strong Safety (Parent: S, DB)

TIER 4 (Lower - 68+ overall starter needed):
  ✓ TE - Tight End
  ✓ DT - Defensive Tackle (Parent: DL)
  ✓ NT - Nose Tackle (Parent: DL)
  ✓ K - Kicker (Parent: ST)
  ✓ P - Punter (Parent: ST)
  ✓ LS - Long Snapper (Parent: ST)
  ✓ FB - Fullback
  ✓ KR - Kick Returner (Parent: ST)
  ✓ PR - Punt Returner (Parent: ST)
```

### Urgency Levels

| Level | Score | Typical Scenarios |
|-------|-------|-------------------|
| **CRITICAL** | 5 | No starter, starter < threshold-5, starter leaving with no replacement |
| **HIGH** | 4 | Starter < threshold, starter leaving, no depth backup |
| **MEDIUM** | 3 | Weak depth, insufficient backups for premium position, aging starter |
| **LOW** | 2 | Starter 80-85 OVR, adequate depth, secondary position |
| **NONE** | 1 | Starter 85+ OVR, good depth, well-staffed position |

---

## 2. Starter Rating Thresholds

| Tier | Positions | Threshold | Below Standard | Example |
|------|-----------|-----------|---|----------|
| 1 | QB, DE, LT, RT | 75 | < 70 = CRITICAL | QB at 68 OVR = CRITICAL need |
| 2 | WR, CB, C, FS, S | 72 | < 67 = CRITICAL | WR at 70 OVR = HIGH need |
| 3 | RB, LB, LG, RG, SS | 70 | < 65 = CRITICAL | LB at 68 OVR = HIGH need |
| 4 | TE, DT, K, P, LS | 68 | < 63 = CRITICAL | DT at 65 OVR = HIGH need |

---

## 3. Urgency Decision Tree

```
START: Analyzing position need

├─ Does team have ANY starter? (depth_order = 1)
│  ├─ NO → CRITICAL (no starter)
│  └─ YES ↓
│
├─ Is starter leaving? (contract expires)
│  ├─ YES & no adequate backup → CRITICAL
│  ├─ YES & have backup → HIGH
│  └─ NO ↓
│
├─ Is starter overall < threshold - 5? (Far below standard)
│  ├─ YES → CRITICAL
│  └─ NO ↓
│
├─ Is starter overall < threshold? (Below standard)
│  ├─ YES → HIGH
│  └─ NO ↓
│
├─ Does position have 0 backups?
│  ├─ YES & Tier 1/2 position → HIGH
│  └─ NO ↓
│
├─ Is starter 75-80 OVR with weak backup depth?
│  ├─ YES → MEDIUM
│  └─ NO ↓
│
├─ Does Tier 1/2 position have < 2 backups?
│  ├─ YES → MEDIUM
│  └─ NO ↓
│
├─ Is starter 80-85 OVR with adequate depth?
│  ├─ YES → LOW
│  └─ NO ↓
│
└─ Starter 85+ OVR with good depth → NONE
```

---

## 4. Position Matching Rules

### Match Types (by specificity)

```
EXACT MATCH (100%):
  Prospect WR → Need WR
  Prospect CB → Need CB
  Prospect LT → Need LT

HIERARCHY MATCH (80%):
  Prospect LG → Need Guard
  Prospect WR → Need Receiver (generic)
  Prospect CB → Need Defensive Back (child position)

GROUP MATCH (60%):
  Prospect LT → Need RG (both Offensive Line)
  Prospect DE → Need DT (both Defensive Line)
  Prospect ILB → Need OLB (both Linebacker)

NO MATCH (0%):
  Prospect WR → Need QB
  Prospect K → Need DE
  Position not in top 5 needs
```

### Position Hierarchy

```
QB
├─ Offense

Offensive Skill Positions:
├─ WR
├─ RB
├─ TE
├─ FB

Offensive Line:
├─ LT → Tackle → OL
├─ RT → Tackle → OL
├─ C → OL
├─ LG → Guard → OL
├─ RG → Guard → OL

Defensive Line:
├─ DE → DL
├─ DT → DL
├─ NT → DL

Linebackers:
├─ MIKE → LB → Defense
├─ OLB → LB → Defense
├─ ILB → LB → Defense
├─ WIL → LB → Defense

Secondary:
├─ CB → DB → Defense
├─ NCB → DB → Defense
├─ FS → Safety → DB → Defense
├─ SS → Safety → DB → Defense
└─ S → DB → Defense

Special Teams:
├─ K → ST
├─ P → ST
├─ LS → ST
├─ KR → ST
└─ PR → ST
```

---

## 5. Highlight Decision Matrix

### Pick Evaluation Highlighting

```
                     Elite 85+ OVR    Very Good 80-85    Good 75-80    Average <75
CRITICAL (5)         🟢 🟢 🟢         🟢 🟢              🟢            ◈
HIGH (4)             🟢 🟢            🟡 🟡              🟡            ◈
MEDIUM (3)           🟢              🟡                ◈             ◈
LOW (2)              🟡              ◈                 ◈             🔴
NONE (0)             ◈              ◈                 ◈             🔴

Legend:
  🟢 Green   = Excellent match (highlight prominently)
  🟡 Yellow  = Good match (solid pick)
  ◈ Neutral = Acceptable (no highlight needed)
  🔴 Red     = Weak match (question the pick)
```

### Color Codes

```
🟢 GREEN   - CRITICAL urgency + Good prospect (80+ OVR)
           - HIGH urgency + Elite prospect (85+ OVR)
           → Display prominently, suggest this pick

🟡 YELLOW  - HIGH urgency + Good prospect (80+ OVR)
           - MEDIUM urgency + Elite prospect
           → Highlight as solid option

◈ NEUTRAL  - MEDIUM urgency + Good prospect
           - LOW urgency + Good prospect
           → Show details but don't highlight

🔴 RED     - LOW urgency + Any prospect
           - NONE urgency + Any prospect
           - NO MATCH (position not in top 5)
           → Suggest better alternatives
```

---

## 6. Real-World Need Examples

### Example 1: Young QB Team

```
Trigger: QB drafted in last 1-2 years (Rookie contract)

Typical Critical Needs:
  1. LEFT TACKLE (protect young QB) - CRITICAL
  2. WIDE RECEIVER (young QB needs weapons) - CRITICAL
  3. TIGHT END (safety valve) - HIGH
  4. CENTER (snaps, protection) - HIGH

Secondary Needs:
  5. DEFENSIVE END (build defense) - MEDIUM

Never Needs:
  - QB (for next 3+ years)
  - ST (kicker/punter/snapper)
```

### Example 2: Aging Star QB (< 2 years left)

```
Trigger: Star QB 35+ years old, contract expiring soon

Typical Critical Needs:
  1. QUARTERBACK (franchise QB in next draft) - CRITICAL
  2. WIDE RECEIVER (set up next QB) - HIGH
  3. LEFT TACKLE (set up next QB) - HIGH
  4. DEFENSIVE END (can't afford to wait) - MEDIUM

Secondary Needs:
  5. CORNERBACK (defense building) - MEDIUM

Note: Team may trade current star QB or ride out final years
```

### Example 3: Rebuilding/Tanking Team

```
Trigger: Young core, missing key foundational pieces

Typical Critical Needs:
  1. CORNERBACK (defense core) - CRITICAL
  2. WIDE RECEIVER (offense weapons) - CRITICAL
  3. DEFENSIVE END (pass rush) - HIGH
  4. OFFENSIVE LINE (protect QB) - HIGH
  5. TIGHT END (receiving depth) - MEDIUM

Focus: Multiple positions in each draft to build foundation
```

### Example 4: Contending Team (Balanced)

```
Trigger: Good overall roster, need incremental upgrades

Typical Needs:
  1. WIDE RECEIVER (skill position depth) - MEDIUM
  2. DEFENSIVE END (pass rush upgrade) - MEDIUM
  3. CORNERBACK (secondary depth) - LOW
  4. LINEBACKER (coverage depth) - LOW
  5. OFFENSIVE LINE (depth rotation) - LOW

Focus: Depth and competition for starters
```

### Example 5: Injured Key Player Replacement

```
Trigger: Star player lost to injury, need emergency replacement

Scenario: Lost Pro-Bowl CB to ACL tear
  1. CORNERBACK (fill Pro-Bowl CB loss) - CRITICAL
  2. SAFETY (secondary help) - HIGH
  3. LINEBACKER (scheme adjustment) - MEDIUM
  (Other team needs fall to secondary priority)

Note: Team likely shifts "win-now" mentality for this need
```

---

## 7. Quick Lookup: Positions by Category

### By Position Group

```
Offense (Skill):
  QB, WR, RB, TE, FB (5 positions)

Offense (Line):
  LT, RT, LG, RG, C (5 positions)

Defense (Line):
  DE, DT, NT (3 positions)

Defense (LB):
  MIKE, OLB, ILB, WIL, LB (5 positions)

Defense (DB):
  CB, FS, SS, S, NCB (5 positions)

Special Teams:
  K, P, LS, KR, PR (5 positions)

TOTAL: 28 unique positions tracked
```

### By Urgency Frequency

```
Most Likely CRITICAL:
  - QB (when no starter or aging out)
  - DE (when no starter quality edge)
  - LT (when young QB vulnerable)

Often HIGH:
  - CB (always valuable, often needed)
  - WR (offense weapon needed)
  - FS/S (safety always valued)
  - OL (protection always needed)

Rarely CRITICAL:
  - K, P, LS (few ever critical)
  - RB (depth available)
  - TE (lower value position)
  - ST returners (depth players)
```

---

## 8. Draft Board Display

### Sample Output

```
═══════════════════════════════════════════════════════════════
                    DRAFT BOARD - TEAM VIEW
═══════════════════════════════════════════════════════════════

TEAM: Detroit Lions (2024 Season)

🟢 CRITICAL PRIORITIES (Must address):
   1. Wide Receiver (Starter 68 OVR, 0 backups)
   2. Left Tackle (Starter 70 OVR, 1 backup)

🟡 HIGH PRIORITIES (Address by R2-3):
   3. Cornerback (Starter 72 OVR, 1 backup)
   4. Tight End (Starter 69 OVR, 0 backups)

◈ MEDIUM PRIORITIES (Fill gaps):
   5. Defensive End (Starter 76 OVR, 2 backups)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AVAILABLE PROSPECTS (Sorted by Team Value):

[Suggest top prospects that match needs, with color coding]

R1, Pick 6:  🟢 DeVonta Smith (WR, 92 OVR) - CRITICAL MATCH
             └─ Addresses WR CRITICAL need - Elite talent

R1, Pick 6:  🟡 Olu Fashanu (LT, 90 OVR) - HIGH MATCH
             └─ Addresses LT HIGH need - Excellent tackle

R1, Pick 6:  🟡 Malachi Starks (CB, 88 OVR) - HIGH MATCH
             └─ Addresses CB HIGH need - Shutdown corner

R1, Pick 6:  ◈ Jalen Daniels (QB, 87 OVR) - NO MATCH
             └─ QB not in top 5 needs (future option only)
```

---

## 9. Database Schema Quick View

### Teams_Needs Table (Reference)

```sql
CREATE TABLE team_needs (
  team_id INT,
  season INT,
  position VARCHAR(50),
  urgency_level INT (1-5),
  starter_overall INT,
  backup_count INT,
  backup_avg_overall FLOAT,
  starter_expiring BOOL,
  reason TEXT,
  PRIMARY KEY (team_id, season, position)
);

-- Example rows:
INSERT INTO team_needs VALUES (22, 2024, 'wide_receiver', 5, 68, 1, 64, false, 'Starter well below standard');
INSERT INTO team_needs VALUES (22, 2024, 'cornerback', 4, 72, 0, 0, false, 'No backup depth');
INSERT INTO team_needs VALUES (22, 2024, 'left_tackle', 3, 75, 1, 70, false, 'Weak depth behind starter');
```

---

## 10. Integration Checklist

### When Starting Draft Simulation

```
☐ Load all 32 teams' needs via TeamNeedsAnalyzer.analyze_team_needs()
☐ Get top 5 needs for each team
☐ Cache needs in memory (1 analysis per team per season)
☐ Store team_needs data in database for future reference
☐ Generate draft boards specific to each team
☐ When evaluating prospects:
  ☐ Check position vs team needs
  ☐ Calculate need match score
  ☐ Apply urgency bonuses to prospect value
  ☐ Display pick evaluation with highlighting
☐ When user makes pick:
  ☐ Evaluate fit vs top needs
  ☐ Show match quality (green/yellow/red)
  ☐ Log pick with need analysis
```

### When Starting Free Agency

```
☐ Re-analyze team needs (contracts may have changed)
☐ Prioritize FA targets in CRITICAL/HIGH positions
☐ Evaluate free agents by position vs needs
☐ Calculate need matching bonuses
☐ Apply GM personality modifiers (if available)
☐ Display recommended targets by need tier
```

### When Evaluating Trades

```
☐ Identify teams with CRITICAL/HIGH needs
☐ Look for teams with excess at other positions
☐ Calculate need-based trade value adjustments
☐ More aggressive trade offers for CRITICAL needs
☐ Use needs analysis to drive trade logic
```

---

## 11. Common Needs Patterns by Week

### Off-Season Timeline

```
MARCH 12 (Free Agency Opens):
  - Re-analyze all team needs
  - Identify expiring contracts
  - Prioritize free agent positions

APRIL (NFL Draft):
  - Needs drive draft selections
  - AI teams pick based on needs
  - User sees recommendations

APRIL-JUNE (FA/Draft Follow-up):
  - Secondary signings fill remaining needs
  - UDFA signings address depth

JUNE-JULY (Roster Cuts):
  - Use position value + need analysis
  - Prioritize keeping starters in need areas
  - Cut depth in well-staffed positions

AUGUST (Final Roster):
  - Validate position minimums
  - Ensure critical needs addressed
  - Check for glaring holes
```

---

## 12. Cheat Sheet: Common Scenarios

### "Is this pick good?"

```
Ask 3 questions:

1. Does prospect position match any of team's top 5 needs?
   └─ NO  → "Weak pick, off-board position" 🔴
   └─ YES → Continue

2. Is the matching need CRITICAL or HIGH urgency?
   └─ NO  → "Solid depth pick" 🟡
   └─ YES → Continue

3. Is prospect elite (85+) or very good (80+)?
   └─ NO  → "Okay fit but could do better" 🟡
   └─ YES → "Excellent match!" 🟢
```

### "What should team do in round X?"

```
Look at unfilled needs:
  - Any CRITICAL needs left? → Address immediately
  - Any HIGH needs left? → Prioritize next
  - Any MEDIUM needs? → Fill if value prospect available
  - Supplemental depth? → Only if all needs addressed
```

### "Does free agent fit?"

```
1. What position is free agent?
2. Is that position in team's top 5 needs?
   └─ NO  → Probably not worth contract
   └─ YES → Check salary cap fit
3. How urgent is the need?
   └─ CRITICAL → Pay premium for quality
   └─ HIGH → Fair market value
   └─ MEDIUM → Discount signings only
```

---

## 13. Position Abbreviations Reference

```
OFFENSE (10):
  QB - Quarterback      | RB - Running Back     | FB - Fullback
  WR - Wide Receiver    | TE - Tight End
  LT - Left Tackle      | LG - Left Guard       | C - Center
  RG - Right Guard      | RT - Right Tackle

DEFENSE (13):
  DE - Defensive End    | DT - Defensive Tackle | NT - Nose Tackle
  LB - Linebacker       | MIKE - Mike LB        | OLB - Outside LB
  ILB - Inside LB       | WIL - Will LB
  CB - Cornerback       | NCB - Nickel CB       | S - Safety
  FS - Free Safety      | SS - Strong Safety

SPECIAL TEAMS (5):
  K - Kicker            | P - Punter            | LS - Long Snapper
  KR - Kick Returner    | PR - Punt Returner

GROUPINGS:
  OL - Offensive Line (all 5 positions)
  DL - Defensive Line (DE, DT, NT)
  DB - Defensive Back (CB, S, FS, SS, NCB)
  ST - Special Teams (all 5 positions)
```

---

**Last Updated**: November 2025
**File**: docs/design/TEAM_NEEDS_ASSIGNMENT_SYSTEM.md (full version)
