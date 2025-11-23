"""
Mock Data Generator for Draft Day Demo

Generates realistic mock prospects, GM personalities, team needs, and draft order.
"""

import random
import sqlite3
import uuid
from datetime import datetime
from typing import List, Dict, Tuple


# Position distributions for 300 prospects
POSITION_DISTRIBUTION = {
    'QB': 30,
    'RB': 24,
    'WR': 36,
    'TE': 18,
    'OL': 42,
    'EDGE': 30,
    'DT': 24,
    'LB': 30,
    'CB': 36,
    'S': 30
}

# College programs (weighted by prospect quality)
COLLEGES = [
    'Alabama', 'Georgia', 'Ohio State', 'LSU', 'Clemson',
    'Michigan', 'Texas', 'USC', 'Oklahoma', 'Florida',
    'Penn State', 'Notre Dame', 'Oregon', 'Florida State', 'Miami',
    'Texas A&M', 'Auburn', 'Tennessee', 'Wisconsin', 'Iowa',
    'Washington', 'Stanford', 'UCLA', 'Michigan State', 'Ole Miss'
]

# First and last names for player generation
FIRST_NAMES = [
    'Marcus', 'DeAndre', 'Tyler', 'Jordan', 'Cameron',
    'Brandon', 'Isaiah', 'Justin', 'Michael', 'Chris',
    'Kevin', 'James', 'Robert', 'David', 'Anthony',
    'Josh', 'Kyle', 'Nick', 'Jake', 'Ryan'
]

LAST_NAMES = [
    'Williams', 'Johnson', 'Smith', 'Brown', 'Davis',
    'Miller', 'Wilson', 'Moore', 'Taylor', 'Anderson',
    'Thomas', 'Jackson', 'White', 'Harris', 'Martin',
    'Thompson', 'Garcia', 'Martinez', 'Robinson', 'Clark'
]

# GM Archetypes and their trait profiles
GM_ARCHETYPES = {
    'BPA': {
        'risk_tolerance': 0.5,
        'win_now_mentality': 0.4,
        'values_potential': 0.8,
        'values_need': 0.3,
        'draft_bpa_tendency': 0.9
    },
    'Win-Now': {
        'risk_tolerance': 0.6,
        'win_now_mentality': 0.9,
        'values_potential': 0.3,
        'values_need': 0.7,
        'draft_bpa_tendency': 0.4
    },
    'Conservative': {
        'risk_tolerance': 0.2,
        'win_now_mentality': 0.5,
        'values_potential': 0.5,
        'values_need': 0.6,
        'draft_bpa_tendency': 0.6
    },
    'Rebuilder': {
        'risk_tolerance': 0.7,
        'win_now_mentality': 0.2,
        'values_potential': 0.9,
        'values_need': 0.4,
        'draft_bpa_tendency': 0.7,
        'rebuilding_patience': 0.9
    },
    'Risk-Tolerant': {
        'risk_tolerance': 0.8,
        'win_now_mentality': 0.5,
        'values_potential': 0.7,
        'values_need': 0.5,
        'draft_bpa_tendency': 0.6
    },
    'Aggressive Trader': {
        'risk_tolerance': 0.7,
        'win_now_mentality': 0.7,
        'values_potential': 0.5,
        'values_need': 0.8,
        'trade_aggressiveness': 0.9,
        'draft_bpa_tendency': 0.5
    }
}

# Position needs for all 32 teams (randomized but realistic)
TEAM_NEEDS_TEMPLATES = [
    ['QB', 'OL', 'EDGE'],
    ['EDGE', 'CB', 'S'],
    ['WR', 'LB', 'OL'],
    ['RB', 'DT', 'CB'],
    ['OL', 'WR', 'LB'],
    ['CB', 'EDGE', 'TE'],
    ['S', 'OL', 'QB'],
    ['LB', 'WR', 'DT']
]


def generate_prospects(cursor: sqlite3.Cursor, dynasty_id: str, season_year: int) -> List[str]:
    """
    Generate 300 realistic draft prospects with proper distributions.

    Args:
        cursor: SQLite cursor
        dynasty_id: Dynasty identifier
        season_year: Draft class year

    Returns:
        List of prospect IDs
    """
    # Create draft class
    class_id = f"draft_class_{season_year}_{dynasty_id}"
    cursor.execute("""
        INSERT INTO draft_classes
        (class_id, season_year, dynasty_id, total_prospects, generated_at, is_finalized)
        VALUES (?, ?, ?, 300, ?, 0)
    """, (class_id, season_year, dynasty_id, datetime.now().isoformat()))

    prospect_ids = []

    # Generate prospects for each position
    for position, count in POSITION_DISTRIBUTION.items():
        for i in range(count):
            prospect_id = str(uuid.uuid4())
            prospect_ids.append(prospect_id)

            # Generate ratings (bell curve distribution)
            overall_rating = _generate_overall_rating()
            potential_rating = _generate_potential_rating(overall_rating)

            # Physical attributes
            age = random.choices([20, 21, 22, 23], weights=[0.1, 0.4, 0.4, 0.1])[0]
            height_inches = random.randint(68, 80)
            weight_lbs = random.randint(180, 320)

            # Skill attributes
            speed = _generate_skill_attribute(overall_rating)
            strength = _generate_skill_attribute(overall_rating)
            awareness = _generate_skill_attribute(overall_rating)
            agility = _generate_skill_attribute(overall_rating)
            stamina = random.randint(75, 95)
            injury_prone = random.randint(20, 80)

            # Ceiling and floor
            ceiling = min(99, potential_rating + random.randint(0, 5))
            floor = max(60, overall_rating - random.randint(5, 15))

            # Archetype and grade
            archetype = _get_position_archetype(position)
            draft_grade = _get_draft_grade(overall_rating)

            # College (weighted by rating)
            college = _get_college_for_rating(overall_rating)

            # Name
            first_name = random.choice(FIRST_NAMES)
            last_name = random.choice(LAST_NAMES)

            cursor.execute("""
                INSERT INTO draft_prospects (
                    prospect_id, class_id, dynasty_id, first_name, last_name,
                    position, college, age, height_inches, weight_lbs,
                    overall_rating, potential_rating, speed, strength, awareness,
                    agility, stamina, injury_prone, ceiling, floor,
                    archetype, draft_grade, is_drafted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                prospect_id, class_id, dynasty_id, first_name, last_name,
                position, college, age, height_inches, weight_lbs,
                overall_rating, potential_rating, speed, strength, awareness,
                agility, stamina, injury_prone, ceiling, floor,
                archetype, draft_grade
            ))

    return prospect_ids


def generate_gm_personalities(cursor: sqlite3.Cursor, dynasty_id: str):
    """
    Assign GM personalities to all 32 teams.

    Args:
        cursor: SQLite cursor
        dynasty_id: Dynasty identifier
    """
    # Distribution of archetypes across 32 teams
    archetype_distribution = {
        'BPA': 8,
        'Win-Now': 6,
        'Conservative': 6,
        'Rebuilder': 5,
        'Risk-Tolerant': 4,
        'Aggressive Trader': 3
    }

    # Build list of archetypes
    archetypes = []
    for archetype, count in archetype_distribution.items():
        archetypes.extend([archetype] * count)

    # Shuffle and assign to teams
    random.shuffle(archetypes)

    for team_id in range(1, 33):
        archetype = archetypes[team_id - 1]
        base_traits = GM_ARCHETYPES[archetype]

        # Add some variation to base traits
        traits = {}
        for trait, value in base_traits.items():
            variation = random.uniform(-0.1, 0.1)
            traits[trait] = max(0.0, min(1.0, value + variation))

        # Fill in missing traits with defaults
        all_traits = {
            'risk_tolerance': traits.get('risk_tolerance', 0.5),
            'win_now_mentality': traits.get('win_now_mentality', 0.5),
            'values_potential': traits.get('values_potential', 0.5),
            'values_need': traits.get('values_need', 0.5),
            'trade_aggressiveness': traits.get('trade_aggressiveness', 0.5),
            'loyalty': 0.5,
            'analytics_driven': random.uniform(0.3, 0.8),
            'player_development_focus': random.uniform(0.4, 0.7),
            'draft_bpa_tendency': traits.get('draft_bpa_tendency', 0.5),
            'free_agency_activity': random.uniform(0.3, 0.7),
            'veteran_preference': random.uniform(0.3, 0.7),
            'salary_cap_flexibility': random.uniform(0.4, 0.8),
            'rebuilding_patience': traits.get('rebuilding_patience', 0.5)
        }

        cursor.execute("""
            INSERT INTO gm_personalities (
                team_id, dynasty_id, archetype,
                risk_tolerance, win_now_mentality, values_potential, values_need,
                trade_aggressiveness, loyalty, analytics_driven, player_development_focus,
                draft_bpa_tendency, free_agency_activity, veteran_preference,
                salary_cap_flexibility, rebuilding_patience
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            team_id, dynasty_id, archetype,
            all_traits['risk_tolerance'], all_traits['win_now_mentality'],
            all_traits['values_potential'], all_traits['values_need'],
            all_traits['trade_aggressiveness'], all_traits['loyalty'],
            all_traits['analytics_driven'], all_traits['player_development_focus'],
            all_traits['draft_bpa_tendency'], all_traits['free_agency_activity'],
            all_traits['veteran_preference'], all_traits['salary_cap_flexibility'],
            all_traits['rebuilding_patience']
        ))


def generate_team_needs(cursor: sqlite3.Cursor, dynasty_id: str):
    """
    Assign position needs to all 32 teams.

    Args:
        cursor: SQLite cursor
        dynasty_id: Dynasty identifier
    """
    for team_id in range(1, 33):
        # Select random need template
        needs = random.choice(TEAM_NEEDS_TEMPLATES).copy()

        # Randomize priorities
        for priority, position in enumerate(needs, start=1):
            urgency = ['HIGH', 'MEDIUM', 'LOW'][priority - 1] if priority <= 3 else 'LOW'

            cursor.execute("""
                INSERT INTO team_needs (team_id, dynasty_id, position, priority, urgency_level)
                VALUES (?, ?, ?, ?, ?)
            """, (team_id, dynasty_id, position, priority, urgency))


def generate_draft_order(cursor: sqlite3.Cursor, dynasty_id: str, season_year: int):
    """
    Generate draft order for 7 rounds (262 picks including compensatory).

    Args:
        cursor: SQLite cursor
        dynasty_id: Dynasty identifier
        season_year: Draft year
    """
    # Randomized draft order (simulates team records)
    team_order = list(range(1, 33))
    random.shuffle(team_order)

    overall_pick = 1

    for round_number in range(1, 8):  # 7 rounds
        # Base picks (32 per round)
        for pick_in_round, team_id in enumerate(team_order, start=1):
            pick_id = f"pick_{season_year}_r{round_number}_p{pick_in_round}"

            cursor.execute("""
                INSERT INTO draft_order (
                    pick_id, dynasty_id, season_year, round_number, pick_in_round,
                    overall_pick, original_team_id, current_team_id, is_compensatory
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                pick_id, dynasty_id, season_year, round_number, pick_in_round,
                overall_pick, team_id, team_id
            ))

            overall_pick += 1

        # Add compensatory picks at end of round 3
        if round_number == 3:
            for i in range(6):  # 6 compensatory picks
                comp_team = random.choice(team_order[16:])  # Give to teams in latter half
                pick_id = f"pick_{season_year}_r{round_number}_comp{i+1}"

                cursor.execute("""
                    INSERT INTO draft_order (
                        pick_id, dynasty_id, season_year, round_number, pick_in_round,
                        overall_pick, original_team_id, current_team_id, is_compensatory
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                """, (
                    pick_id, dynasty_id, season_year, round_number, 33 + i,
                    overall_pick, comp_team, comp_team
                ))

                overall_pick += 1


def populate_mock_data(cursor: sqlite3.Cursor, dynasty_id: str, season_year: int) -> Dict:
    """
    Generate all mock data for the draft simulation.

    Args:
        cursor: SQLite cursor
        dynasty_id: Dynasty identifier
        season_year: Draft year

    Returns:
        Dictionary with counts of generated items
    """
    # Create dynasty record
    cursor.execute("""
        INSERT INTO dynasties (
            dynasty_id, dynasty_name, current_season, created_at, is_active
        ) VALUES (?, ?, ?, ?, 1)
    """, (dynasty_id, "Draft Day Demo Dynasty", season_year, datetime.now().isoformat()))

    # Generate all data
    prospect_ids = generate_prospects(cursor, dynasty_id, season_year)
    generate_gm_personalities(cursor, dynasty_id)
    generate_team_needs(cursor, dynasty_id)
    generate_draft_order(cursor, dynasty_id, season_year)

    # Count picks
    cursor.execute("SELECT COUNT(*) FROM draft_order WHERE dynasty_id = ?", (dynasty_id,))
    pick_count = cursor.fetchone()[0]

    return {
        'prospects': len(prospect_ids),
        'teams': 32,
        'picks': pick_count
    }


# Helper functions

def _generate_overall_rating() -> int:
    """Generate overall rating with bell curve distribution."""
    # Elite prospects (85+): ~4%
    # High prospects (75-84): ~10%
    # Mid prospects (65-74): ~30%
    # Low prospects (55-64): ~40%
    # Undraftable (<55): ~16%

    rand = random.random()
    if rand < 0.04:
        return random.randint(85, 95)
    elif rand < 0.14:
        return random.randint(75, 84)
    elif rand < 0.44:
        return random.randint(65, 74)
    elif rand < 0.84:
        return random.randint(55, 64)
    else:
        return random.randint(45, 54)


def _generate_potential_rating(overall_rating: int) -> int:
    """Generate potential rating based on overall rating."""
    # Potential is typically higher than overall for young prospects
    bonus = random.randint(0, 15)
    return min(99, overall_rating + bonus)


def _generate_skill_attribute(overall_rating: int) -> int:
    """Generate individual skill attribute correlated with overall rating."""
    # Skills vary around overall rating
    variance = random.randint(-10, 10)
    return max(40, min(99, overall_rating + variance))


def _get_position_archetype(position: str) -> str:
    """Get archetype for position."""
    archetypes = {
        'QB': ['Pocket Passer', 'Scrambler', 'Dual Threat'],
        'RB': ['Power Back', 'Speed Back', '3-Down Back'],
        'WR': ['Deep Threat', 'Possession', 'Slot'],
        'TE': ['Blocking', 'Receiving', 'Hybrid'],
        'OL': ['Road Grader', 'Pass Protector', 'Athletic'],
        'EDGE': ['Speed Rusher', 'Power Rusher', '3-4 OLB'],
        'DT': ['Run Stuffer', 'Pass Rusher', '3-Tech'],
        'LB': ['Coverage', 'Run Stopper', 'Blitzer'],
        'CB': ['Man Coverage', 'Zone', 'Press'],
        'S': ['Box Safety', 'Free Safety', 'Hybrid']
    }
    return random.choice(archetypes.get(position, ['Standard']))


def _get_draft_grade(overall_rating: int) -> str:
    """Convert overall rating to draft grade."""
    if overall_rating >= 85:
        return 'A'
    elif overall_rating >= 75:
        return 'B'
    elif overall_rating >= 65:
        return 'C'
    elif overall_rating >= 55:
        return 'D'
    else:
        return 'F'


def _get_college_for_rating(overall_rating: int) -> str:
    """Select college weighted by prospect rating."""
    if overall_rating >= 80:
        # Elite prospects from top programs
        return random.choice(COLLEGES[:10])
    elif overall_rating >= 70:
        # Good prospects from good programs
        return random.choice(COLLEGES[:18])
    else:
        # All programs
        return random.choice(COLLEGES)
