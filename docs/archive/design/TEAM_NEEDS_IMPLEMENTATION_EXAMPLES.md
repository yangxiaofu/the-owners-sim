# Team Needs Implementation Examples

**Status**: Code Examples & Implementation Patterns
**Related Files**:
- `src/offseason/team_needs_analyzer.py` - Core implementation
- `src/offseason/draft_manager.py` - Draft integration
- `src/offseason/free_agency_manager.py` - Free agency integration

---

## 1. Basic Usage Examples

### 1.1 Analyze Single Team's Needs

```python
from offseason.team_needs_analyzer import TeamNeedsAnalyzer, NeedUrgency

# Initialize analyzer
analyzer = TeamNeedsAnalyzer(
    database_path="data/database/nfl_simulation.db",
    dynasty_id="my_dynasty"
)

# Get all needs for a team
all_needs = analyzer.analyze_team_needs(
    team_id=22,  # Detroit Lions
    season=2024,
    include_future_contracts=True
)

# Get top 5 needs
top_5 = analyzer.get_top_needs(
    team_id=22,
    season=2024,
    limit=5
)

# Print needs
for need in top_5:
    print(f"{need['position']}: {need['urgency'].name} ({need['reason']})")

# Output:
# wide_receiver: CRITICAL (Starter well below standard (68 overall))
# cornerback: HIGH (No backup depth)
# offensive_line: MEDIUM (Weak depth behind starter)
# defensive_end: LOW (Starter solid, could upgrade depth)
# running_back: LOW (Starter solid, could upgrade depth)
```

### 1.2 Analyze All 32 Teams

```python
from offseason.team_needs_analyzer import TeamNeedsAnalyzer

analyzer = TeamNeedsAnalyzer(
    database_path="data/database/nfl_simulation.db",
    dynasty_id="my_dynasty"
)

# Get needs for all 32 teams
all_team_needs = {}

for team_id in range(1, 33):
    team_needs = analyzer.get_top_needs(
        team_id=team_id,
        season=2024,
        limit=5
    )
    all_team_needs[team_id] = team_needs

# Usage
for team_id, needs in all_team_needs.items():
    if needs:
        print(f"\nTeam {team_id}:")
        for need in needs:
            urgency_icon = {
                'CRITICAL': '⚠️',
                'HIGH': '⬆️',
                'MEDIUM': '➡️',
                'LOW': '◈'
            }.get(need['urgency'].name, '•')

            print(f"  {urgency_icon} {need['position']}: {need['urgency'].name}")
```

### 1.3 Filter Needs by Urgency

```python
def get_critical_needs(team_needs: List[Dict]) -> List[Dict]:
    """Get only CRITICAL urgency needs."""
    return [n for n in team_needs if n['urgency_score'] == 5]

def get_high_priority_needs(team_needs: List[Dict]) -> List[Dict]:
    """Get HIGH and CRITICAL needs."""
    return [n for n in team_needs if n['urgency_score'] >= 4]

def get_needs_by_tier(team_needs: List[Dict], tier: int) -> List[Dict]:
    """Get needs for specific position tier (1-4)."""
    return [
        n for n in team_needs
        if analyzer._get_position_tier(n['position']) == tier
    ]

# Usage
analyzer = TeamNeedsAnalyzer("database.db", "dynasty_1")
all_needs = analyzer.analyze_team_needs(22, 2024)

critical = get_critical_needs(all_needs)
if critical:
    print(f"Detroit has {len(critical)} critical needs")
    for need in critical:
        print(f"  - {need['position']}")
```

---

## 2. Draft Integration Examples

### 2.1 Evaluate Prospect for Team

```python
def evaluate_prospect_for_team(
    prospect: Dict,  # {player_id, position, overall, name}
    team_id: int,
    team_needs: List[Dict]
) -> Dict:
    """
    Evaluate how well a prospect fits team's needs.

    Returns:
        {
            'position_match': 'EXACT' | 'HIERARCHY' | 'GROUP' | 'NO_MATCH',
            'match_urgency': int (0-5),
            'reasoning': str,
            'highlight': bool,
            'recommendation': str,
            'expected_value': int (0-100)
        }
    """
    prospect_position = prospect['position']
    prospect_overall = prospect['overall']

    # Find matching need
    matching_need = None
    match_type = None

    for need in team_needs:
        if prospect_position == need['position']:
            # Exact match
            matching_need = need
            match_type = 'EXACT'
            break
        elif is_hierarchy_match(prospect_position, need['position']):
            # Hierarchy match (e.g., LG → Guard)
            matching_need = need
            match_type = 'HIERARCHY'
            break
        elif is_group_match(prospect_position, need['position']):
            # Group match (e.g., LT → RG, both OL)
            matching_need = need
            match_type = 'GROUP'
            break

    if not matching_need:
        return {
            'position_match': 'NO_MATCH',
            'match_urgency': 0,
            'reasoning': f"{prospect_position} not in top 5 needs",
            'highlight': False,
            'recommendation': "Off-board for this team",
            'expected_value': 20  # Low value for off-board pick
        }

    # Calculate expected value
    urgency = matching_need['urgency_score']

    # Value bonuses
    quality_bonus = min((prospect_overall - 75) * 2, 30)
    match_bonus = {'EXACT': 20, 'HIERARCHY': 15, 'GROUP': 10}.get(match_type, 0)
    urgency_bonus = urgency * 15

    expected_value = min(100, quality_bonus + match_bonus + urgency_bonus)

    # Determine highlighting
    highlight = (urgency >= 4 and prospect_overall >= 80) or \
                (urgency == 5 and prospect_overall >= 75)

    # Recommendation
    if highlight and urgency >= 4:
        recommendation = "STRONG PICK" if urgency == 5 else "SOLID PICK"
    elif match_type == 'NO_MATCH':
        recommendation = "POOR PICK - Off-board"
    elif urgency <= 2:
        recommendation = "WEAK PICK - Low priority need"
    else:
        recommendation = "ACCEPTABLE PICK"

    return {
        'position_match': match_type,
        'match_urgency': urgency,
        'reasoning': matching_need['reason'],
        'highlight': highlight,
        'recommendation': recommendation,
        'expected_value': expected_value
    }


# Usage in draft selection
from offseason.draft_manager import DraftManager

draft_mgr = DraftManager(
    database_path="data/database/nfl_simulation.db",
    dynasty_id="my_dynasty",
    season_year=2024
)

analyzer = TeamNeedsAnalyzer("data/database/nfl_simulation.db", "my_dynasty")

# Get team's needs
team_needs = analyzer.get_top_needs(team_id=22, season=2024, limit=5)

# Evaluate prospects
prospects = draft_mgr.get_draft_board(team_id=22, limit=10)

for prospect in prospects:
    evaluation = evaluate_prospect_for_team(
        prospect=prospect,
        team_id=22,
        team_needs=team_needs
    )

    icon = {
        'EXACT': '✓',
        'HIERARCHY': '↑',
        'GROUP': '≈',
        'NO_MATCH': '✗'
    }.get(evaluation['position_match'], '?')

    highlight = '⭐' if evaluation['highlight'] else ' '

    print(f"{highlight} {icon} {prospect['position']:15} "
          f"({prospect['overall']} OVR) - {evaluation['recommendation']}")
```

### 2.2 AI Draft Selection with Needs

```python
def select_best_prospect_for_team(
    available_prospects: List[Dict],
    team_id: int,
    team_needs: List[Dict],
    gm: Optional[GMArchetype] = None
) -> Dict:
    """
    Select best prospect considering team needs.
    """
    best_prospect = None
    best_score = -1

    for prospect in available_prospects:
        # Objective value (overall rating)
        base_value = prospect['overall']

        # Position need bonus
        position_urgency = 0
        for need in team_needs:
            if prospect['position'] == need['position']:
                position_urgency = need['urgency_score']
                break

        # Apply urgency bonus
        need_boost = {
            5: 15,  # CRITICAL
            4: 8,   # HIGH
            3: 3,   # MEDIUM
            2: 0,   # LOW
            1: 0    # NONE
        }.get(position_urgency, 0)

        adjusted_value = base_value + need_boost

        # Apply GM personality modifiers if available
        if gm:
            # GM might reach for certain positions, fall back from others
            gm_modifier = get_gm_preference_modifier(gm, prospect['position'])
            adjusted_value += gm_modifier

        if adjusted_value > best_score:
            best_score = adjusted_value
            best_prospect = prospect

    return best_prospect


def get_gm_preference_modifier(gm: GMArchetype, position: str) -> float:
    """
    Get GM personality modifier for position preference.

    Example:
      - Aggressive GM: +10 for DE/CB (defense), -5 for K/P (special teams)
      - Conservative GM: +5 for OL, -5 for WR (skill position)
    """
    if gm.philosophy == 'aggressive':
        return {
            'defensive_end': 10,
            'cornerback': 10,
            'linebacker': 5,
            'kicker': -5,
            'punter': -5
        }.get(position, 0)

    elif gm.philosophy == 'conservative':
        return {
            'left_tackle': 8,
            'right_tackle': 8,
            'center': 5,
            'wide_receiver': -3,
            'running_back': -2
        }.get(position, 0)

    else:  # balanced
        return 0
```

---

## 3. Free Agency Integration Examples

### 3.1 Prioritize Free Agents by Team Need

```python
def prioritize_free_agents(
    free_agent_pool: List[Dict],  # {player_id, position, overall, salary_ask}
    team_id: int,
    team_needs: List[Dict],
    salary_cap_available: int
) -> List[Dict]:
    """
    Rank free agents by how well they fit team needs.
    """
    ranked_fas = []

    for fa in free_agent_pool:
        # Check position match
        position_urgency = 0
        for need in team_needs:
            if fa['position'] == need['position']:
                position_urgency = need['urgency_score']
                break

        if position_urgency == 0:
            # Not in top 5 needs - lower priority
            continue

        # Check salary fit
        if fa['salary_ask'] > salary_cap_available * 0.1:
            # Expensive - lower priority
            salary_score = 50
        else:
            salary_score = 100

        # Calculate match score
        match_score = position_urgency * 20 + salary_score

        ranked_fas.append({
            'player': fa,
            'urgency': position_urgency,
            'match_score': match_score,
            'salary_fit': salary_score
        })

    # Sort by match score (highest first)
    ranked_fas.sort(key=lambda x: x['match_score'], reverse=True)

    return ranked_fas


# Usage
analyzer = TeamNeedsAnalyzer("database.db", "dynasty_1")
team_needs = analyzer.get_top_needs(team_id=22, season=2024, limit=5)

free_agents = get_free_agent_pool()  # From FreeAgencyManager
cap_available = get_team_salary_cap(team_id=22, season=2024)

ranked_fas = prioritize_free_agents(
    free_agent_pool=free_agents,
    team_id=22,
    team_needs=team_needs,
    salary_cap_available=cap_available
)

print("FREE AGENT TARGETS (by team need):")
for rank, target in enumerate(ranked_fas[:10], 1):
    print(f"{rank}. {target['player']['name']} ({target['player']['position']}) "
          f"- Salary Cap Fit: {target['salary_fit']}/100")
```

### 3.2 Target Free Agents by Need Tier

```python
def get_fa_targets_for_critical_needs(
    free_agent_pool: List[Dict],
    team_needs: List[Dict],
    team_budget: int
) -> Dict[str, List[Dict]]:
    """
    Group free agents by team need urgency.
    """
    targets = {
        'CRITICAL': [],
        'HIGH': [],
        'MEDIUM': [],
        'LOW': []
    }

    critical_positions = {n['position'] for n in team_needs if n['urgency_score'] == 5}
    high_positions = {n['position'] for n in team_needs if n['urgency_score'] == 4}
    medium_positions = {n['position'] for n in team_needs if n['urgency_score'] == 3}
    low_positions = {n['position'] for n in team_needs if n['urgency_score'] == 2}

    for fa in free_agent_pool:
        if fa['position'] in critical_positions:
            targets['CRITICAL'].append(fa)
        elif fa['position'] in high_positions:
            targets['HIGH'].append(fa)
        elif fa['position'] in medium_positions:
            targets['MEDIUM'].append(fa)
        elif fa['position'] in low_positions:
            targets['LOW'].append(fa)

    # Sort each tier by overall rating
    for tier in targets:
        targets[tier].sort(key=lambda x: x['overall'], reverse=True)

    return targets


# Usage
targets = get_fa_targets_for_critical_needs(
    free_agent_pool=free_agents,
    team_needs=team_needs,
    team_budget=15_000_000
)

print("CRITICAL NEED TARGETS:")
for fa in targets['CRITICAL'][:5]:
    print(f"  {fa['name']} ({fa['position']}, {fa['overall']} OVR)")

print("\nHIGH PRIORITY TARGETS:")
for fa in targets['HIGH'][:5]:
    print(f"  {fa['name']} ({fa['position']}, {fa['overall']} OVR)")
```

---

## 4. Display & UI Examples

### 4.1 CLI Display of Team Needs

```python
def display_team_needs_cli(
    team_id: int,
    team_name: str,
    team_needs: List[Dict],
    season: int
):
    """Display team needs in CLI format."""

    print(f"\n{'=' * 70}")
    print(f"{'TEAM NEEDS ANALYSIS':^70}")
    print(f"{team_name} - {season} Season")
    print('=' * 70)

    # Group by urgency
    urgency_groups = {
        'CRITICAL': [n for n in team_needs if n['urgency_score'] == 5],
        'HIGH': [n for n in team_needs if n['urgency_score'] == 4],
        'MEDIUM': [n for n in team_needs if n['urgency_score'] == 3],
        'LOW': [n for n in team_needs if n['urgency_score'] == 2],
    }

    urgency_icons = {
        'CRITICAL': '⚠️',
        'HIGH': '⬆️',
        'MEDIUM': '➡️',
        'LOW': '◈'
    }

    for urgency_level in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        needs = urgency_groups[urgency_level]
        if not needs:
            continue

        icon = urgency_icons[urgency_level]
        print(f"\n📍 {urgency_level} NEEDS ({len(needs)}):")

        for need in needs:
            print(f"  {icon} {need['position'].upper():20}")
            print(f"      Starter: {need['starter_overall']:3} OVR " +
                  f"(Threshold: {get_tier_threshold(need['position']):3}+)")
            print(f"      Backups: {need['depth_count']:1} " +
                  f"(Avg: {need['avg_depth_overall']:.0f} OVR)")
            if need['starter_leaving']:
                print(f"      ⚠️  Starter contract EXPIRING!")
            print(f"      {need['reason']}\n")

    print('=' * 70)


def get_tier_threshold(position: str) -> int:
    """Get threshold for position tier."""
    tier_map = {
        'quarterback': 75, 'defensive_end': 75,
        'left_tackle': 75, 'right_tackle': 75,
        'wide_receiver': 72, 'cornerback': 72, 'center': 72,
        'free_safety': 72, 'safety': 72,
        'running_back': 70, 'linebacker': 70,
        'left_guard': 70, 'right_guard': 70, 'strong_safety': 70
    }
    return tier_map.get(position, 68)  # Default to Tier 4


# Usage
analyzer = TeamNeedsAnalyzer("database.db", "dynasty_1")
team_needs = analyzer.analyze_team_needs(team_id=22, season=2024)

display_team_needs_cli(
    team_id=22,
    team_name="Detroit Lions",
    team_needs=team_needs,
    season=2024
)
```

### 4.2 Draft Pick Evaluation Display

```python
def display_pick_evaluation(
    team_id: int,
    team_name: str,
    pick_number: int,
    prospect: Dict,
    evaluation: Dict
):
    """Display detailed pick evaluation."""

    # Color mapping
    color_map = {
        'EXACT': '✓',
        'HIERARCHY': '↑',
        'GROUP': '≈',
        'NO_MATCH': '✗'
    }

    # Recommendation icon
    rec_icon_map = {
        'STRONG PICK': '🟢',
        'SOLID PICK': '🟡',
        'ACCEPTABLE PICK': '◈',
        'WEAK PICK': '🔴',
        'POOR PICK': '❌'
    }

    print(f"\n{'=' * 70}")
    print(f"{'PICK EVALUATION':^70}")
    print('=' * 70)

    print(f"\nTEAM: {team_name} (Pick #{pick_number})")
    print(f"\nPROSPECT:")
    print(f"  Name:     {prospect['name']}")
    print(f"  Position: {prospect['position'].upper()}")
    print(f"  Overall:  {prospect['overall']} OVR")
    print(f"  Projected Range: Picks {prospect.get('projected_min', '?')}-" +
          f"{prospect.get('projected_max', '?')}")

    print(f"\nMATCH ANALYSIS:")
    match_icon = color_map[evaluation['position_match']]
    print(f"  Match Type: {match_icon} {evaluation['position_match']}")
    print(f"  Need Urgency: {evaluation['match_urgency']}/5")
    print(f"  Expected Value: {evaluation['expected_value']}/100")
    print(f"  Reasoning: {evaluation['reasoning']}")

    rec = evaluation['recommendation']
    rec_icon = rec_icon_map.get(rec, '?')

    print(f"\nRECOMMENDATION:")
    print(f"  {rec_icon} {rec}")

    if evaluation['highlight']:
        print(f"\n  ⭐ HIGHLIGHTED - Strong fit for team needs!")
    else:
        print(f"\n  Consider other options to address higher priorities")

    print('=' * 70)


# Usage in draft simulation
evaluation = evaluate_prospect_for_team(
    prospect={'player_id': 1, 'name': 'DeVonta Smith',
              'position': 'wide_receiver', 'overall': 92},
    team_id=22,
    team_needs=team_needs
)

display_pick_evaluation(
    team_id=22,
    team_name="Detroit Lions",
    pick_number=6,
    prospect={'name': 'DeVonta Smith', 'position': 'wide_receiver', 'overall': 92},
    evaluation=evaluation
)
```

---

## 5. Database Query Examples

### 5.1 Query Team Needs from Database

```python
def get_team_needs_from_db(
    database_path: str,
    team_id: int,
    season: int
) -> List[Dict]:
    """Query stored team needs from database."""
    import sqlite3

    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            position,
            urgency_level,
            starter_overall,
            backup_count,
            backup_avg_overall,
            starter_expiring,
            reason
        FROM team_needs
        WHERE team_id = ? AND season = ?
        ORDER BY urgency_level DESC
    """, (team_id, season))

    needs = []
    for row in cursor.fetchall():
        needs.append({
            'position': row['position'],
            'urgency_score': row['urgency_level'],
            'starter_overall': row['starter_overall'],
            'depth_count': row['backup_count'],
            'avg_depth_overall': row['backup_avg_overall'],
            'starter_leaving': bool(row['starter_expiring']),
            'reason': row['reason']
        })

    conn.close()
    return needs
```

### 5.2 Store Analyzed Needs to Database

```python
def store_team_needs(
    database_path: str,
    team_id: int,
    season: int,
    team_needs: List[Dict]
):
    """Store analyzed needs to database for future reference."""
    import sqlite3

    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    # Create table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS team_needs (
            team_id INTEGER,
            season INTEGER,
            position TEXT,
            urgency_level INTEGER,
            starter_overall INTEGER,
            backup_count INTEGER,
            backup_avg_overall REAL,
            starter_expiring BOOLEAN,
            reason TEXT,
            PRIMARY KEY (team_id, season, position)
        )
    """)

    # Store each need
    for need in team_needs:
        cursor.execute("""
            INSERT OR REPLACE INTO team_needs
            (team_id, season, position, urgency_level, starter_overall,
             backup_count, backup_avg_overall, starter_expiring, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            team_id,
            season,
            need['position'],
            need['urgency_score'],
            need['starter_overall'],
            need['depth_count'],
            need['avg_depth_overall'],
            1 if need['starter_leaving'] else 0,
            need['reason']
        ))

    conn.commit()
    conn.close()
```

---

## 6. Complete Example: Full Draft Simulation with Needs

```python
def simulate_draft_with_needs_display():
    """Complete example of draft simulation with needs analysis."""

    from offseason.team_needs_analyzer import TeamNeedsAnalyzer
    from offseason.draft_manager import DraftManager
    from constants.team_ids import TeamIDs

    # Initialize
    database_path = "data/database/nfl_simulation.db"
    dynasty_id = "my_dynasty"
    season = 2024

    analyzer = TeamNeedsAnalyzer(database_path, dynasty_id)
    draft_mgr = DraftManager(database_path, dynasty_id, season)

    # Generate draft class
    print("Generating draft class...")
    draft_class = draft_mgr.generate_draft_class(size=300)
    print(f"✓ Generated {len(draft_class)} prospects\n")

    # Get needs for all 32 teams
    print("Analyzing team needs...")
    all_team_needs = {}
    for team_id in range(1, 33):
        all_team_needs[team_id] = analyzer.get_top_needs(
            team_id=team_id,
            season=season,
            limit=5
        )
    print("✓ Analyzed all 32 teams\n")

    # Simulate draft
    print(f"{'=' * 80}")
    print(f"{'2024 NFL DRAFT SIMULATION':^80}")
    print(f"{'=' * 80}\n")

    available_prospects = draft_class.copy()
    draft_results = []

    # Get draft order
    from database.draft_order_database_api import DraftOrderDatabaseAPI
    draft_order_api = DraftOrderDatabaseAPI(database_path)
    draft_order = draft_order_api.get_draft_order(dynasty_id, season)

    # Process each pick
    for pick in draft_order:
        if not available_prospects:
            print(f"\n⚠️  No more prospects available! Draft ended at pick {pick.overall_pick}\n")
            break

        team_id = pick.current_team_id
        team_needs = all_team_needs[team_id]

        # Select best prospect for team
        best_prospect = select_best_prospect_for_team(
            available_prospects,
            team_id,
            team_needs
        )

        # Evaluate fit
        evaluation = evaluate_prospect_for_team(
            best_prospect,
            team_id,
            team_needs
        )

        # Display pick
        highlight = "⭐" if evaluation['highlight'] else "  "
        position = best_prospect['position'].upper()
        urgency_icon = {
            'EXACT': '✓',
            'HIERARCHY': '↑',
            'GROUP': '≈',
            'NO_MATCH': '✗'
        }.get(evaluation['position_match'], '?')

        print(f"{highlight} Pick {pick.overall_pick:3d} (R{pick.round_number}.{pick.pick_in_round:2d}) - "
              f"Team {team_id:2d}: "
              f"{best_prospect['name']:20s} {position:10s} "
              f"({best_prospect['overall']} OVR) "
              f"[{urgency_icon} {evaluation['recommendation']}]")

        # Execute pick
        draft_mgr.make_draft_selection(
            round_num=pick.round_number,
            pick_num=pick.pick_in_round,
            player_id=best_prospect['player_id'],
            team_id=team_id
        )

        # Remove from available
        available_prospects = [
            p for p in available_prospects
            if p['player_id'] != best_prospect['player_id']
        ]

        draft_results.append({
            'pick_num': pick.overall_pick,
            'team_id': team_id,
            'prospect': best_prospect,
            'evaluation': evaluation
        })

    print(f"\n{'=' * 80}")
    print(f"✓ Draft Complete! {len(draft_results)} picks executed")
    print(f"{'=' * 80}\n")

    # Summary statistics
    exact_matches = sum(1 for r in draft_results if r['evaluation']['position_match'] == 'EXACT')
    critical_filled = sum(
        1 for r in draft_results
        if r['evaluation']['match_urgency'] == 5
    )

    print(f"Summary:")
    print(f"  Exact Position Matches: {exact_matches}/{len(draft_results)} ({exact_matches*100//len(draft_results)}%)")
    print(f"  Critical Needs Filled: {critical_filled}")

    return draft_results
```

---

## 7. Testing Examples

### 7.1 Unit Tests

```python
import unittest
from offseason.team_needs_analyzer import TeamNeedsAnalyzer, NeedUrgency


class TestTeamNeedsAnalyzer(unittest.TestCase):

    def setUp(self):
        """Setup test fixtures."""
        self.analyzer = TeamNeedsAnalyzer(
            database_path="data/database/nfl_simulation.db",
            dynasty_id="test_dynasty"
        )

    def test_critical_need_no_starter(self):
        """Test that missing starter creates CRITICAL need."""
        # Mock depth chart with no starter
        depth_chart = {
            'wide_receiver': [
                {'depth_order': 2, 'overall': 75, 'player_id': 2},
                {'depth_order': 3, 'overall': 70, 'player_id': 3}
            ]
        }

        need = self.analyzer._analyze_position_need(
            position='wide_receiver',
            depth_chart=depth_chart,
            expiring_players=[]
        )

        self.assertEqual(need['urgency'], NeedUrgency.CRITICAL)
        self.assertEqual(need['starter_overall'], 0)

    def test_high_need_poor_starter(self):
        """Test that poor starter creates HIGH need."""
        depth_chart = {
            'wide_receiver': [
                {'depth_order': 1, 'overall': 70, 'player_id': 1},  # Below 72 threshold
                {'depth_order': 2, 'overall': 65, 'player_id': 2}
            ]
        }

        need = self.analyzer._analyze_position_need(
            position='wide_receiver',
            depth_chart=depth_chart,
            expiring_players=[]
        )

        self.assertEqual(need['urgency'], NeedUrgency.HIGH)
        self.assertEqual(need['starter_overall'], 70)

    def test_medium_need_weak_depth(self):
        """Test that good starter with weak backups creates MEDIUM need."""
        depth_chart = {
            'wide_receiver': [
                {'depth_order': 1, 'overall': 80, 'player_id': 1},  # Good starter
                {'depth_order': 2, 'overall': 65, 'player_id': 2}   # Weak backup
            ]
        }

        need = self.analyzer._analyze_position_need(
            position='wide_receiver',
            depth_chart=depth_chart,
            expiring_players=[]
        )

        self.assertEqual(need['urgency'], NeedUrgency.MEDIUM)
```

---

**Last Updated**: November 2025
**Location**: docs/design/TEAM_NEEDS_IMPLEMENTATION_EXAMPLES.md
