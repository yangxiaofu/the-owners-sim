# Draft Demo Team Archetype Assignments

**Version**: 1.0.0
**Last Updated**: 2025-11-22
**Purpose**: Official team-to-archetype mapping for draft AI demo

---

## Distribution Summary

| Archetype | Count | % of League | Philosophy |
|-----------|-------|-------------|------------|
| **BPA (Balanced)** | 8 | 25% | Best Player Available, talent-focused |
| **Win-Now** | 6 | 19% | Championship window, polished prospects |
| **Conservative** | 6 | 19% | Risk-averse, high-floor picks |
| **Rebuilder** | 5 | 16% | Long-term upside, developmental prospects |
| **Risk-Tolerant (Star Chaser)** | 4 | 13% | Boom-or-bust, elite ceiling targets |
| **Aggressive Trader** | 3 | 9% | Trade-active, scheme fit priority |

**Total**: 32 teams

---

## Complete Team Assignments

### BPA GMs (8 teams - 25%)
*Philosophy: Talent over need, strict board adherence, value accumulation*

| Team ID | Team Name | Notes |
|---------|-----------|-------|
| 1 | Arizona Cardinals | Balanced approach with methodical drafting |
| 8 | Denver Broncos | Trust their evaluations, BPA-focused |
| 12 | Green Bay Packers | Historic draft-and-develop, board-strict |
| 14 | Indianapolis Colts | Value-based drafting philosophy |
| 19 | Minnesota Vikings | Balanced roster building approach |
| 24 | Pittsburgh Steelers | Traditional Steelers draft philosophy |
| 27 | Seattle Seahawks | Best available talent, position-flexible |
| 31 | Tennessee Titans | Methodical, grade-based selections |

---

### Win-Now GMs (6 teams - 19%)
*Philosophy: Championship window urgency, polished prospects, immediate impact*

| Team ID | Team Name | Notes |
|---------|-----------|-------|
| 4 | Buffalo Bills | Allen's window, title contention mode |
| 6 | Cincinnati Bengals | Burrow's window, playoff-ready picks |
| 15 | Kansas City Chiefs | Mahomes dynasty window, proven talent |
| 23 | Philadelphia Eagles | Recent SB appearance, sustained contention |
| 26 | San Francisco 49ers | Elite roster, missing pieces only |
| 30 | Tampa Bay Buccaneers | Competitive roster, veteran-focused |

---

### Conservative GMs (6 teams - 19%)
*Philosophy: Risk-averse, high-floor prospects, proven college production*

| Team ID | Team Name | Notes |
|---------|-----------|-------|
| 11 | Houston Texans | Steady rebuild, safe picks |
| 13 | Jacksonville Jaguars | Conservative approach, low variance |
| 20 | New Orleans Saints | Cap constraints, need reliability |
| 24 | Pittsburgh Steelers | Steelers Way: proven, safe picks |
| 28 | Baltimore Ravens | Smart drafting, avoid busts |
| 32 | New York Jets | Risk-averse, production-focused |

**Note**: Pittsburgh Steelers (24) can appear in both BPA and Conservative categories depending on demo needs. Use Conservative for demos emphasizing risk aversion, BPA for talent-focused scenarios.

---

### Rebuilders (5 teams - 16%)
*Philosophy: Long-term upside, youth-focused, ceiling over floor*

| Team ID | Team Name | Notes |
|---------|-----------|-------|
| 3 | Carolina Panthers | Full rebuild mode, youth movement |
| 5 | Chicago Bears | Building foundation, patient approach |
| 9 | Detroit Lions | Transitioning rebuild, draft-centric |
| 21 | New England Patriots | Post-Brady rebuild, accumulate youth |
| 22 | New York Giants | Foundational rebuild, long timeline |

---

### Risk-Tolerant GMs (4 teams - 13%)
*Philosophy: Boom-or-bust, elite ceiling targets, All-Pro upside*

| Team ID | Team Name | Notes |
|---------|-----------|-------|
| 10 | Dallas Cowboys | Jerry Jones influence, star-chasing |
| 16 | Las Vegas Raiders | Aggressive picks, big swings |
| 25 | Washington Commanders | High-risk, high-reward approach |
| 29 | Los Angeles Chargers | Target elite traits, accept volatility |

---

### Aggressive Traders (3 teams - 9%)
*Philosophy: Trade-active, scheme fit priority, versatility valued*

| Team ID | Team Name | Notes |
|---------|-----------|-------|
| 2 | Atlanta Falcons | Active in trade market, flexibility |
| 7 | Cleveland Browns | Aggressive trade approach |
| 17 | Los Angeles Rams | Historic trade activity (Stafford, Ramsey) |
| 18 | Miami Dolphins | Frequent draft-day trades |

---

## Changes from Current Assignments

### Teams Moved to Different Archetypes

| Team ID | Team Name | OLD Archetype | NEW Archetype | Reason |
|---------|-----------|---------------|---------------|--------|
| 2 | Atlanta Falcons | Balanced | Aggressive Trader | Better fits trade-active approach |
| 9 | Detroit Lions | Draft Hoarder | Rebuilder | Draft Hoarder → Rebuilder for draft demo clarity |
| 11 | Houston Texans | Draft Hoarder | Conservative | Better represents steady rebuild |
| 16 | Las Vegas Raiders | Aggressive Trader | Risk-Tolerant | Better fits boom-bust philosophy |
| 24 | Pittsburgh Steelers | Balanced | Conservative | Traditional Steelers safe drafting |
| 28 | Baltimore Ravens | Star Chaser | Conservative | Smart, risk-averse drafting style |
| 30 | Tampa Bay Buccaneers | Balanced | Win-Now | Competitive window, playoff roster |

**Note**: These changes are **demo-specific recommendations**. Current production assignments in `src/config/gm_profiles/` remain valid for free agency and roster cuts. Draft demo can use this mapping for clearer archetype demonstrations.

---

## Usage in Draft Demo

### Loading Archetypes

```python
from team_management.gm_archetype_factory import GMArchetypeFactory

# Initialize factory
factory = GMArchetypeFactory()

# Get team's archetype
team_id = 15  # Kansas City Chiefs
archetype = factory.get_team_archetype(team_id)

print(f"Team: {archetype.name}")
print(f"Win-Now: {archetype.win_now_mentality}")  # 0.85 for Chiefs
print(f"Risk Tolerance: {archetype.risk_tolerance}")  # 0.7 for Chiefs
```

### Generating Commentary

```python
from offseason.draft_commentary_generator import DraftCommentaryGenerator

# Initialize generator
gen = DraftCommentaryGenerator()

# Generate commentary
prospect = {
    'first_name': 'Caleb',
    'last_name': 'Williams',
    'position': 'quarterback',
    'overall': 92,
    'ceiling': 95,
    'floor': 88,
    'age': 21
}

commentary = gen.generate_commentary(
    team_id=3,  # Carolina Panthers (Rebuilder)
    archetype='rebuilder',
    selected_prospect=prospect,
    team_needs=[
        {'position': 'quarterback', 'urgency_score': 5, 'urgency': 'CRITICAL'}
    ],
    pick_position=1
)

print(commentary)
# Output: "Rebuilding Carolina Panthers swing for upside with Caleb Williams (95 ceiling)"
```

---

## Demo Scenario Recommendations

### Scenario 1: Contrasting Philosophies (Picks 1-3)

- **Pick 1: Carolina Panthers (Rebuilder)** - Drafts high-ceiling QB
- **Pick 2: New York Jets (Conservative)** - Drafts safe, high-floor OT
- **Pick 3: Dallas Cowboys (Risk-Tolerant)** - Reaches for boom-bust EDGE

**Demonstrates**: Different GMs value same prospects differently

---

### Scenario 2: Win-Now vs Rebuild (Picks 10-15)

- **Pick 10: Kansas City Chiefs (Win-Now)** - Drafts polished WR (age 23)
- **Pick 15: Chicago Bears (Rebuilder)** - Drafts raw CB (age 20, high ceiling)

**Demonstrates**: Age and polish preferences across archetypes

---

### Scenario 3: BPA vs Need (Picks 20-25)

- **Pick 20: Green Bay Packers (BPA)** - Drafts best player (RB) despite depth
- **Pick 25: Jacksonville Jaguars (Conservative)** - Reaches for safe LB (critical need)

**Demonstrates**: BPA philosophy vs need-based drafting

---

## Validation Notes

### Current State

As of 2025-11-22, the production GM profiles in `src/config/gm_profiles/` use these assignments:

- **Balanced**: 10 teams (31% of league)
- **Win-Now**: 5 teams (16%)
- **Rebuilder**: 4 teams (13%)
- **Aggressive Trader**: 4 teams (13%)
- **Star Chaser**: 4 teams (13%)
- **Conservative**: 3 teams (9%)
- **Draft Hoarder**: 2 teams (6%)

### Demo Recommendations

This document recommends adjusted distribution for **draft demo clarity**:

- Consolidate Draft Hoarder → Rebuilder (similar philosophy)
- Move some Balanced → Conservative/Win-Now/Aggressive Trader (more distinct)
- Better archetype variety across 32 teams

---

## Future Enhancements

### Phase 3 Additions

1. **Trade-Up/Trade-Down Patterns**: Different archetypes have different trade tendencies
2. **Round-Specific Behavior**: Early vs late round risk tolerance
3. **Positional Archetypes**: Some GMs have position biases (e.g., "never draft RB early")

### Advanced Commentary

1. **Comparative Commentary**: "Unlike rebuilder [Team A], win-now [Team B] drafts polished [Player]"
2. **Historical Context**: "[Team] continues their trend of targeting [Position] early"
3. **Division Dynamics**: "Responding to rival [Team]'s [Position] selection"

---

**End of Documentation**
