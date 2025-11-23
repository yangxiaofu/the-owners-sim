# GM Draft Demo Patterns

**Version**: 1.0.0
**Last Updated**: 2025-11-22
**Purpose**: Define GM archetypes and commentary patterns for draft AI demo

---

## Table of Contents

1. [Overview](#overview)
2. [Recommended Draft Archetypes](#recommended-draft-archetypes)
3. [Team Assignment Strategy](#team-assignment-strategy)
4. [Commentary Generation System](#commentary-generation-system)
5. [Demo Implementation Guide](#demo-implementation-guide)

---

## Overview

This document defines 6 distinct GM archetypes optimized for **draft demo visualization**, with specific commentary patterns that illustrate how GM personalities influence draft decisions.

### Design Goals

1. **Variety**: 6 archetypes covering full spectrum of draft philosophies
2. **Clarity**: Each archetype has distinct, observable behavior
3. **Balance**: 32 teams distributed across archetypes (no overweighting)
4. **Storytelling**: Commentary templates make GM personality visible to user

---

## Recommended Draft Archetypes

Based on the existing 7 base archetypes, we recommend **6 core archetypes** for the draft demo:

### 1. Win-Now GM (Championship Window)

**Base Archetype**: `win_now`

**Draft Philosophy**:
- Prefers polished, high-floor prospects (age 23-24)
- Values immediate impact over long-term upside
- Prioritizes premium positions (QB, Edge, LT)
- Risk-averse: Avoids boom/bust prospects

**Key Traits**:
```json
{
  "win_now_mentality": 0.85,
  "veteran_preference": 0.75,
  "risk_tolerance": 0.7,
  "premium_position_focus": 0.7
}
```

**Draft Modifier Impact**:
- **Age Penalty**: Raw 20-21 year olds get -8 to -10 points
- **Age Bonus**: Polished 23-24 year olds get +4 to +5 points
- **Floor Preference**: High-floor prospects get +5 to +10 points
- **Ceiling Discount**: High-ceiling prospects get -5 to -10 points

**Example Teams**: Kansas City Chiefs, Buffalo Bills, Cincinnati Bengals, Philadelphia Eagles, San Francisco 49ers

**Commentary Templates**:
- "Win-now GM {team} targets polished prospect {player} for immediate impact"
- "{team}'s championship window drives selection of NFL-ready {position}"
- "With SB aspirations, {team} avoids project player {alt_player}, selects safe pick {player}"
- "{team} prioritizes proven production over upside with {player} selection"

---

### 2. Rebuilder GM (Future-Focused)

**Base Archetype**: `rebuilder`

**Draft Philosophy**:
- Values high-ceiling, developmental prospects (age 20-21)
- Willing to draft "projects" with elite athletic traits
- Focuses on accumulating young talent
- Prioritizes premium positions for long-term foundation

**Key Traits**:
```json
{
  "win_now_mentality": 0.2,
  "veteran_preference": 0.3,
  "risk_tolerance": 0.35,
  "draft_pick_value": 0.85,
  "premium_position_focus": 0.8
}
```

**Draft Modifier Impact**:
- **Youth Bonus**: 20-21 year olds get +3 to +5 points
- **Youth Tolerance**: No age penalty for raw prospects
- **Ceiling Preference**: High-ceiling prospects get +8 to +12 points
- **Floor Tolerance**: No penalty for low-floor prospects

**Example Teams**: Carolina Panthers, Chicago Bears, New England Patriots, New York Giants

**Commentary Templates**:
- "Rebuilding {team} swings for high-ceiling prospect {player}"
- "{team} prioritizes long-term upside over immediate impact with {player}"
- "Patient approach by {team}: {player} has elite traits despite raw technique"
- "{team}'s multi-year rebuild allows risk on developmental {position}"

---

### 3. Risk-Tolerant GM (Boom or Bust)

**Base Archetype**: `star_chaser` (modified with higher risk_tolerance)

**Draft Philosophy**:
- Aggressively pursues elite ceiling prospects (ceiling - overall > 10)
- Values superstar potential over consistency
- Willing to reach for players with explosive traits
- Chases "home run" picks

**Key Traits**:
```json
{
  "risk_tolerance": 0.95,
  "star_chasing": 0.9,
  "win_now_mentality": 0.75,
  "premium_position_focus": 0.85
}
```

**Draft Modifier Impact**:
- **Ceiling Multiplier**: 1.4x weight on ceiling attribute
- **Upside Bonus**: (ceiling - overall) > 10 gets +15 to +20 points
- **Floor Penalty**: Minimal penalty for low floors (-2 to -5 points)
- **Elite Traits**: Athletic freaks get +10 bonus

**Example Teams**: Dallas Cowboys, Las Vegas Raiders, Washington Commanders, Los Angeles Chargers

**Commentary Templates**:
- "Risk-tolerant {team} bets on explosive upside of {player}"
- "{team} chases superstar potential with boom-or-bust pick {player}"
- "High-risk, high-reward: {team} targets elite ceiling of {player}"
- "{team} willing to gamble on raw {position} {player} with All-Pro traits"

---

### 4. Conservative GM (Safe Picks)

**Base Archetype**: `conservative`

**Draft Philosophy**:
- Exclusively drafts high-floor, low-risk prospects
- Values production and polish over athleticism
- Avoids any prospect with character concerns or injury history
- Builds through consistency and smart drafting

**Key Traits**:
```json
{
  "risk_tolerance": 0.1,
  "cap_management": 0.85,
  "veteran_preference": 0.7,
  "loyalty": 0.75
}
```

**Draft Modifier Impact**:
- **Floor Multiplier**: 1.2x weight on floor attribute
- **High-Floor Bonus**: (overall - floor) ≤ 5 gets +10 to +15 points
- **Ceiling Discount**: High-ceiling prospects get -10 to -15 points
- **Production Bonus**: College production stats get +5 bonus

**Example Teams**: Pittsburgh Steelers, Jacksonville Jaguars, New Orleans Saints, New York Jets

**Commentary Templates**:
- "Conservative {team} sticks to safe, high-floor prospect {player}"
- "{team} avoids risk with proven college producer {player}"
- "No gambles for {team}: {player} offers NFL-ready skills"
- "{team}'s risk-averse GM targets low-variance pick in {player}"

---

### 5. BPA GM (Best Player Available)

**Base Archetype**: `balanced` (modified with lower need weighting)

**Draft Philosophy**:
- Pure talent evaluation, minimal need weighting
- Drafts best player on board regardless of position
- Builds through value accumulation
- Willing to stockpile same positions if talent dictates

**Key Traits**:
```json
{
  "risk_tolerance": 0.5,
  "win_now_mentality": 0.5,
  "draft_pick_value": 0.5,
  "loyalty": 0.5,
  "premium_position_focus": 0.6
}
```

**Draft Modifier Impact**:
- **Need Bonus Reduction**: Need bonuses reduced by 50%
- **Value Focus**: +5 bonus if prospect falls >10 picks from projection
- **Talent Purity**: No position bias modifiers
- **Grade-Based**: Strict adherence to draft grade

**Example Teams**: Green Bay Packers, Baltimore Ravens, Arizona Cardinals, Denver Broncos, Minnesota Vikings

**Commentary Templates**:
- "BPA philosophy: {team} selects top-graded {player} despite depth at {position}"
- "{team} ignores positional need, targets best available talent in {player}"
- "Value-driven pick: {team} capitalizes on {player}'s slide"
- "{team} trusts their board, selects {player} over need at {alt_position}"

---

### 6. Aggressive Trader GM (Positional Flexibility)

**Base Archetype**: `aggressive_trader`

**Draft Philosophy**:
- Highly active in trading up/down
- Drafts for scheme fit and versatility
- Values players who can play multiple positions
- Willing to reach for specific targets

**Key Traits**:
```json
{
  "risk_tolerance": 0.75,
  "trade_frequency": 0.85,
  "win_now_mentality": 0.6,
  "deadline_activity": 0.9
}
```

**Draft Modifier Impact**:
- **Versatility Bonus**: Multi-position players get +8 to +12 points
- **Trade-Up Willingness**: Higher likelihood to reach for targets
- **Scheme Fit**: +10 bonus for perfect scheme matches
- **Positional Discount**: Less penalty for reaching

**Example Teams**: Cleveland Browns, Los Angeles Rams, Miami Dolphins, Tampa Bay Buccaneers, Atlanta Falcons

**Commentary Templates**:
- "Active trader {team} targets versatile {player}"
- "{team}'s aggressive GM secures scheme-perfect fit in {player}"
- "Trade-happy {team} moves up for multi-position threat {player}"
- "{team} values flexibility, selects {position}-flex prospect {player}"

---

## Team Assignment Strategy

### Distribution (32 Teams)

| Archetype | Count | % of League |
|-----------|-------|-------------|
| BPA GM | 8 | 25% |
| Win-Now GM | 6 | 19% |
| Conservative GM | 6 | 19% |
| Rebuilder GM | 5 | 16% |
| Risk-Tolerant GM | 4 | 13% |
| Aggressive Trader GM | 3 | 9% |

**Design Rationale**:
- **BPA GMs** (25%): Most common, represents balanced approach
- **Win-Now + Conservative** (38%): Majority of teams prioritize safety
- **Rebuilder + Risk-Tolerant** (29%): Smaller group willing to gamble
- **Aggressive Trader** (9%): Rarest, only most active front offices

### Recommended Team Assignments

#### BPA GMs (8 teams)
1. Arizona Cardinals
2. Denver Broncos
3. Green Bay Packers
4. Indianapolis Colts
5. Minnesota Vikings
6. Baltimore Ravens
7. Seattle Seahawks
8. Tennessee Titans

#### Win-Now GMs (6 teams)
4. Buffalo Bills
6. Cincinnati Bengals
15. Kansas City Chiefs
23. Philadelphia Eagles
26. San Francisco 49ers
28. Baltimore Ravens → **MOVE to Tampa Bay (30)**

#### Conservative GMs (6 teams)
13. Jacksonville Jaguars
20. New Orleans Saints
24. Pittsburgh Steelers
32. New York Jets
**ADD**: Houston Texans (11)
**ADD**: Washington Commanders (25) → **CHANGE to Risk-Tolerant**

#### Rebuilders (5 teams)
3. Carolina Panthers
5. Chicago Bears
21. New England Patriots
22. New York Giants
**ADD**: Tennessee Titans (31) → **MOVE to BPA**

#### Risk-Tolerant GMs (4 teams)
10. Dallas Cowboys
25. Washington Commanders
29. Los Angeles Chargers
**ADD**: Las Vegas Raiders (16)

#### Aggressive Traders (3 teams)
7. Cleveland Browns
17. Los Angeles Rams
18. Miami Dolphins

### Updated Complete Assignment

```python
TEAM_ARCHETYPE_MAP = {
    # BPA GMs (8 teams - 25%)
    1: "balanced",  # Arizona Cardinals
    2: "aggressive_trader",  # Atlanta Falcons
    8: "balanced",  # Denver Broncos
    12: "balanced",  # Green Bay Packers
    14: "balanced",  # Indianapolis Colts
    19: "balanced",  # Minnesota Vikings
    24: "balanced",  # Pittsburgh Steelers → CHANGE to conservative
    27: "balanced",  # Seattle Seahawks
    31: "balanced",  # Tennessee Titans

    # Win-Now GMs (6 teams - 19%)
    4: "win_now",  # Buffalo Bills
    6: "win_now",  # Cincinnati Bengals
    15: "win_now",  # Kansas City Chiefs
    23: "win_now",  # Philadelphia Eagles
    26: "win_now",  # San Francisco 49ers
    30: "win_now",  # Tampa Bay Buccaneers

    # Conservative GMs (6 teams - 19%)
    11: "conservative",  # Houston Texans → CHANGE from draft_hoarder
    13: "conservative",  # Jacksonville Jaguars
    20: "conservative",  # New Orleans Saints
    24: "conservative",  # Pittsburgh Steelers
    28: "conservative",  # Baltimore Ravens → CHANGE from star_chaser
    32: "conservative",  # New York Jets

    # Rebuilders (5 teams - 16%)
    3: "rebuilder",  # Carolina Panthers
    5: "rebuilder",  # Chicago Bears
    9: "rebuilder",  # Detroit Lions → CHANGE from draft_hoarder
    21: "rebuilder",  # New England Patriots
    22: "rebuilder",  # New York Giants

    # Risk-Tolerant GMs (4 teams - 13%)
    10: "star_chaser",  # Dallas Cowboys
    16: "star_chaser",  # Las Vegas Raiders → CHANGE from aggressive_trader
    25: "star_chaser",  # Washington Commanders
    29: "star_chaser",  # Los Angeles Chargers

    # Aggressive Traders (3 teams - 9%)
    7: "aggressive_trader",  # Cleveland Browns
    17: "aggressive_trader",  # Los Angeles Rams
    18: "aggressive_trader",  # Miami Dolphins
}
```

---

## Commentary Generation System

### Commentary Template Structure

```python
COMMENTARY_TEMPLATES = {
    "win_now": {
        "high_floor_pick": [
            "{team} targets polished {position} {player} for immediate impact",
            "Championship window drives {team}'s selection of NFL-ready {player}",
            "{team} prioritizes proven production with {player} ({overall} OVR, high floor)",
        ],
        "avoid_project": [
            "With title aspirations, {team} passes on project {alt_player}, selects safe {player}",
            "{team}'s win-now approach avoids raw {alt_player} ({alt_overall} OVR, low floor)",
        ],
        "premium_position": [
            "{team} addresses championship need at {position} with {player}",
            "Elite {position} {player} fits {team}'s contention timeline",
        ],
    },

    "rebuilder": {
        "high_ceiling_pick": [
            "Rebuilding {team} swings for upside with {player} ({ceiling} ceiling)",
            "{team} prioritizes long-term potential over polish with raw {player}",
            "Patient {team} invests in developmental {position} {player}",
        ],
        "youth_bonus": [
            "{team}'s multi-year rebuild allows gamble on 20-year-old {player}",
            "Young {player} ({age}) fits {team}'s long-term timeline",
        ],
        "premium_foundation": [
            "Building foundation: {team} secures premium {position} {player}",
            "{team} prioritizes cornerstone talent at {position} with {player}",
        ],
    },

    "star_chaser": {
        "boom_or_bust": [
            "Risk-tolerant {team} bets on explosive upside of {player}",
            "{team} chases superstar potential with boom-or-bust {player}",
            "High-risk, high-reward: {team} targets {player}'s {ceiling} ceiling",
        ],
        "elite_traits": [
            "{team} willing to gamble on All-Pro traits of raw {player}",
            "Elite athleticism drives {team}'s selection of {player}",
        ],
        "reach": [
            "{team} reaches for {player} ({projected_pick} projection) due to elite ceiling",
            "Aggressive {team} moves ahead of market on boom prospect {player}",
        ],
    },

    "conservative": {
        "safe_pick": [
            "Conservative {team} sticks to high-floor prospect {player}",
            "{team} avoids risk with proven college producer {player}",
            "No gambles for {team}: {player} offers NFL-ready skills",
        ],
        "production_focus": [
            "{team} values {player}'s extensive college production",
            "Proven performer {player} fits {team}'s risk-averse approach",
        ],
        "avoid_boom_bust": [
            "{team} passes on volatile {alt_player}, selects safe {player}",
            "Risk-averse {team} avoids {alt_player}'s low floor",
        ],
    },

    "balanced": {
        "bpa": [
            "BPA philosophy: {team} selects top-graded {player}",
            "{team} ignores positional need, targets best available {player}",
            "Value-driven pick: {team} capitalizes on {player}'s slide",
        ],
        "position_depth": [
            "{team} trusts their board, drafts {player} despite depth at {position}",
            "Talent over need: {team} adds {position} {player}",
        ],
        "grade_drop": [
            "{team} refuses to reach, selects top remaining player {player}",
            "Strict to their board, {team} takes {player} ({overall} OVR)",
        ],
    },

    "aggressive_trader": {
        "versatility": [
            "Active trader {team} targets versatile {player}",
            "{team} values {player}'s multi-position flexibility",
        ],
        "scheme_fit": [
            "{team}'s aggressive GM secures scheme-perfect {player}",
            "Scheme match drives {team}'s selection of {player}",
        ],
        "trade_activity": [
            "Trade-happy {team} moves up for {player}",
            "{team} executes trade to secure priority target {player}",
        ],
    },
}
```

### Commentary Selection Algorithm

```python
def generate_draft_commentary(
    team_id: int,
    archetype: str,
    selected_prospect: dict,
    team_needs: list,
    available_prospects: list,
    pick_position: int
) -> str:
    """
    Generate contextual draft commentary based on GM archetype.

    Args:
        team_id: Team making selection
        archetype: GM archetype key
        selected_prospect: Dict with player info (name, position, overall, ceiling, floor, age)
        team_needs: List of team need dicts
        available_prospects: List of remaining prospects
        pick_position: Current pick number

    Returns:
        Formatted commentary string
    """
    # Get team name
    team_name = get_team_name(team_id)

    # Extract prospect data
    player_name = f"{selected_prospect['first_name']} {selected_prospect['last_name']}"
    position = selected_prospect['position']
    overall = selected_prospect['overall']
    ceiling = selected_prospect.get('ceiling', overall + 5)
    floor = selected_prospect.get('floor', overall - 5)
    age = selected_prospect.get('age', 21)
    projected_min = selected_prospect.get('projected_pick_min', pick_position - 5)
    projected_max = selected_prospect.get('projected_pick_max', pick_position + 5)

    # Determine commentary context
    is_high_floor = (overall - floor) <= 5
    is_high_ceiling = (ceiling - overall) >= 10
    is_reach = pick_position < (projected_min - 5)
    is_value = pick_position > (projected_max + 10)
    is_premium_pos = position in ['quarterback', 'left_tackle', 'defensive_end', 'cornerback']
    is_critical_need = any(n['urgency_score'] >= 5 and n['position'] == position for n in team_needs)

    # Select template category
    templates = COMMENTARY_TEMPLATES.get(archetype, COMMENTARY_TEMPLATES['balanced'])

    if archetype == 'win_now':
        if is_high_floor:
            category = 'high_floor_pick'
        elif is_premium_pos:
            category = 'premium_position'
        else:
            category = 'avoid_project'

    elif archetype == 'rebuilder':
        if is_high_ceiling:
            category = 'high_ceiling_pick'
        elif age <= 21:
            category = 'youth_bonus'
        elif is_premium_pos:
            category = 'premium_foundation'
        else:
            category = 'high_ceiling_pick'

    elif archetype == 'star_chaser':
        if is_high_ceiling:
            category = 'boom_or_bust'
        elif is_reach:
            category = 'reach'
        else:
            category = 'elite_traits'

    elif archetype == 'conservative':
        if is_high_floor:
            category = 'safe_pick'
        else:
            category = 'production_focus'

    elif archetype == 'balanced':
        if is_value:
            category = 'bpa'
        elif not is_critical_need:
            category = 'position_depth'
        else:
            category = 'grade_drop'

    elif archetype == 'aggressive_trader':
        if selected_prospect.get('versatile', False):
            category = 'versatility'
        else:
            category = 'scheme_fit'

    # Select random template from category
    import random
    template = random.choice(templates[category])

    # Format template
    commentary = template.format(
        team=team_name,
        player=player_name,
        position=position.replace('_', ' ').title(),
        overall=overall,
        ceiling=ceiling,
        floor=floor,
        age=age,
        projected_pick=f"{projected_min}-{projected_max}",
    )

    return commentary
```

---

## Demo Implementation Guide

### Integration with `test_draft_ai_demo.py`

**Recommended Changes**:

1. **Add GM Archetype Loading**:
```python
from team_management.gm_archetype_factory import GMArchetypeFactory

# In main()
factory = GMArchetypeFactory()
```

2. **Modify Scenario Evaluation to Include Commentary**:
```python
def run_scenario_test(draft_manager, scenario, available_prospects, factory):
    # ... existing evaluation code ...

    # Get team's GM archetype
    archetype = factory.get_team_archetype(scenario['team_id'])

    # Generate commentary
    commentary = generate_draft_commentary(
        team_id=scenario['team_id'],
        archetype=archetype.name.lower().replace(' ', '_').replace('-', '_'),
        selected_prospect=best['prospect'],
        team_needs=scenario['team_needs'],
        available_prospects=available_prospects,
        pick_position=scenario['pick_position']
    )

    print(f"\n💬 {commentary}")
```

3. **Add Archetype Summary Section**:
```python
print("\n" + "=" * 80)
print("🎭 GM ARCHETYPE BEHAVIORS")
print("=" * 80)
for r in results:
    archetype = factory.get_team_archetype(r['team_id'])
    print(f"Pick {r['pick']}: {archetype.name} GM (Team {r['team_id']}) - {r['selected']}")
    print(f"  Risk Tolerance: {archetype.risk_tolerance:.2f} | "
          f"Win-Now: {archetype.win_now_mentality:.2f} | "
          f"Draft Value: {archetype.draft_pick_value:.2f}")
```

### Expected Demo Output Example

```
================================================================================
🏈 Scenario 1: QB-Needy Team (Pick #1)
================================================================================

📋 Team 1 Needs (Pick #1):
   CRITICAL   - quarterback           (urgency: 5)
   HIGH       - left_tackle            (urgency: 4)
   MEDIUM     - wide_receiver          (urgency: 3)

💡 Expected: Caleb Williams (QB) - CRITICAL need + best prospect
   Why: QB need is CRITICAL (+15 bonus), Williams is elite (92 OVR)

🔍 Evaluating Top Prospects:
Prospect                       Pos    OVR   Need Bonus   Final Score
--------------------------------------------------------------------------------
Caleb Williams                 quarterback 92    +15          107.0
Joe Alt                        left_tackle 89    +8           97.0
Marvin Harrison Jr             wide_receiver 91    +3           94.0
Jared Verse                    defensive_end 90    0            90.0

✅ AI SELECTS: Caleb Williams (quarterback, 92 OVR) [Score: 107.0]

🎭 GM ARCHETYPE: Rebuilder
   Risk Tolerance: 0.35 | Win-Now: 0.20 | Draft Value: 0.85

💬 Rebuilding Arizona Cardinals swing for upside with Caleb Williams (92 ceiling)
   "Multi-year rebuild allows Cardinals to secure franchise quarterback with elite long-term potential"
```

---

## Validation Checklist

### Demo Requirements

- [ ] All 6 archetypes represented in demo scenarios
- [ ] Commentary templates test for each archetype
- [ ] Edge cases handled (ties, multiple critical needs, BPA vs need conflicts)
- [ ] Commentary variables populate correctly (team, player, position, etc.)
- [ ] Archetype distribution matches recommended 32-team split
- [ ] Commentary accurately reflects GM decision-making logic

### Code Quality

- [ ] Commentary generation function has unit tests
- [ ] Template formatting validated (no missing variables)
- [ ] Integration with existing `DraftManager` seamless
- [ ] No breaking changes to `test_draft_ai_demo.py` structure
- [ ] Performance acceptable (commentary generation <10ms per pick)

---

## Future Enhancements

### Phase 3 Additions

1. **Trade Commentary**: Commentary for trade-up/trade-down decisions
2. **Multi-Pick Narratives**: Connect multiple picks for same team
3. **Surprise Factor**: Highlight unexpected picks vs archetype expectations
4. **Historical Comparisons**: "Similar to when [Team] drafted [Player] in [Year]"

### Advanced Commentary

1. **Context Awareness**: Reference previous picks in round
2. **Division Dynamics**: "Responds to rival [Team]'s pick of [Player]"
3. **Scheme Fit Details**: "Perfect fit for [Coordinator]'s [Scheme] defense"
4. **Draft Class Themes**: "Continues trend of [Position] dominance in 2025 class"

---

**End of Documentation**
