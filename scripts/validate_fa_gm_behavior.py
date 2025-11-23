"""
Free Agency GM Behavior Validation Script

Validates that GM personalities demonstrably influence free agency contract values.

Usage:
    python scripts/validate_fa_gm_behavior.py

Success Criteria:
    - Win-Now teams pay ≥15% more than Rebuilder teams (for all signings)
    - Star Chaser teams pay more for elite players (90+ OVR) than Balanced teams
    - Conservative teams pay ≥10% less overall than Win-Now teams
"""

import sys
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from offseason.free_agency_manager import FreeAgencyManager
from team_management.gm_archetype_factory import GMArchetypeFactory
from team_management.gm_archetype import GMArchetype
from transactions.personality_modifiers import TeamContext


def create_mock_fa_pool() -> List[Dict[str, Any]]:
    """
    Create diverse free agent pool for simulation.

    Returns:
        List of 30 mock free agents with varied attributes
    """
    fa_pool = []
    player_id = 1000

    # Elite tier (90+ OVR) - 5 players
    elite_players = [
        ("Elite QB", "quarterback", 93, 28),
        ("Elite Edge", "edge_rusher", 92, 27),
        ("Elite WR", "wide_receiver", 91, 26),
        ("Elite CB", "cornerback", 91, 29),
        ("Elite LT", "left_tackle", 90, 30),
    ]

    for name, position, overall, age in elite_players:
        fa_pool.append({
            'player_id': f'FA{player_id}',
            'player_name': name,
            'position': position,
            'overall': overall,
            'age': age,
            'years_pro': age - 22,
            'injury_prone': False
        })
        player_id += 1

    # Starter tier (75-85 OVR) - 10 players
    starter_players = [
        ("Starter QB", "quarterback", 82, 26),
        ("Starter RB", "running_back", 79, 25),
        ("Starter WR1", "wide_receiver", 81, 27),
        ("Starter WR2", "wide_receiver", 77, 28),
        ("Starter OT", "offensive_tackle", 80, 29),
        ("Starter Edge", "edge_rusher", 78, 26),
        ("Starter DT", "defensive_tackle", 76, 30),
        ("Starter LB", "linebacker", 79, 27),
        ("Starter CB", "cornerback", 80, 25),
        ("Starter S", "safety", 78, 28),
    ]

    for name, position, overall, age in starter_players:
        fa_pool.append({
            'player_id': f'FA{player_id}',
            'player_name': name,
            'position': position,
            'overall': overall,
            'age': age,
            'years_pro': age - 22,
            'injury_prone': False
        })
        player_id += 1

    # Depth tier (65-75 OVR) - 15 players
    positions = ["quarterback", "running_back", "wide_receiver", "offensive_tackle",
                 "edge_rusher", "linebacker", "cornerback", "safety"]

    for i in range(15):
        position = positions[i % len(positions)]
        fa_pool.append({
            'player_id': f'FA{player_id}',
            'player_name': f'Depth {position.replace("_", " ").title()}',
            'position': position,
            'overall': 65 + (i % 10),  # 65-74 range
            'age': 24 + (i % 8),  # 24-31 age range
            'years_pro': 2 + (i % 6),
            'injury_prone': i % 5 == 0  # 20% injury prone
        })
        player_id += 1

    return fa_pool


def create_test_teams() -> List[Dict[str, Any]]:
    """
    Create test teams with diverse GM archetypes.

    Returns:
        List of team configurations
    """
    return [
        # Win-Now teams (championship urgency)
        {'team_id': 15, 'archetype': 'Win-Now', 'name': 'Kansas City Chiefs'},
        {'team_id': 26, 'archetype': 'Win-Now', 'name': 'San Francisco 49ers'},

        # Rebuilder teams (patient, future-focused)
        {'team_id': 1, 'archetype': 'Rebuilder', 'name': 'Arizona Cardinals'},
        {'team_id': 5, 'archetype': 'Rebuilder', 'name': 'Chicago Bears'},

        # Star Chaser teams (elite talent pursuit)
        {'team_id': 10, 'archetype': 'Star Chaser', 'name': 'Dallas Cowboys'},
        {'team_id': 16, 'archetype': 'Star Chaser', 'name': 'Las Vegas Raiders'},

        # Conservative teams (cap discipline)
        {'team_id': 21, 'archetype': 'Conservative', 'name': 'New England Patriots'},
        {'team_id': 24, 'archetype': 'Conservative', 'name': 'Pittsburgh Steelers'},

        # Balanced teams (neutral approach)
        {'team_id': 12, 'archetype': 'Balanced', 'name': 'Green Bay Packers'},
        {'team_id': 23, 'archetype': 'Balanced', 'name': 'Philadelphia Eagles'},
    ]


def simulate_team_fa_period(
    team_id: int,
    team_name: str,
    archetype_name: str,
    fa_pool: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Simulate entire free agency period for a single team.

    Uses direct evaluation approach to bypass database dependencies.

    Args:
        team_id: Team ID (1-32)
        team_name: Team name for display
        archetype_name: GM archetype name
        fa_pool: Available free agent pool

    Returns:
        List of signings made by this team
    """
    from offseason.market_value_calculator import MarketValueCalculator
    from team_management.players.player import Player

    # Load GM archetype
    gm_factory = GMArchetypeFactory()
    team_gm = gm_factory.get_team_archetype(team_id)

    # Create mock team context
    team_context = TeamContext(
        team_id=team_id,
        season=2025,
        wins=8,  # Mock record
        losses=8,
        playoff_position=None,
        games_out_of_playoff=2,
        cap_space=50_000_000,  # $50M cap space
        cap_percentage=0.25,
        top_needs=['quarterback', 'edge_rusher', 'left_tackle'],
        is_deadline=False,
        is_offseason=True
    )

    # Market value calculator
    market_calc = MarketValueCalculator()

    # Simulate signings
    all_signings = []
    available_fas = fa_pool.copy()

    # Simulate 3 days (Elite, Starter, Depth)
    days_config = [
        (1, {'min_overall': 85, 'max_signings': 2, 'tier_name': 'Elite'}),
        (8, {'min_overall': 75, 'max_signings': 3, 'tier_name': 'Starters'}),
        (16, {'min_overall': 65, 'max_signings': 5, 'tier_name': 'Depth'}),
    ]

    for day, tier_config in days_config:
        signings_today = 0

        # Sort FAs by overall rating (highest first) for more realistic behavior
        # Star chasers will naturally get higher OVR players first
        sorted_fas = sorted(
            [fa for fa in available_fas if fa['overall'] >= tier_config['min_overall']],
            key=lambda x: x['overall'],
            reverse=True
        )

        for fa in sorted_fas:
            if signings_today >= tier_config['max_signings']:
                break

            # Generate contract offer (base market value)
            contract = market_calc.calculate_player_value(
                position=fa['position'],
                overall=fa['overall'],
                age=fa.get('age', 27),
                years_pro=fa.get('years_pro', 4)
            )

            # Create minimal Player object for modifier method
            player = Player(
                name=fa['player_name'],
                number=0,
                primary_position=fa['position'],
                player_id=fa['player_id']
            )
            player.overall = fa['overall']
            player.age = fa.get('age', 27)
            player.injury_prone = fa.get('injury_prone', False)

            # Apply personality-based modifier to contract
            from transactions.personality_modifiers import PersonalityModifiers
            modified_contract = PersonalityModifiers.apply_free_agency_modifier(
                player=player,
                market_value=contract,
                gm=team_gm,
                team_context=team_context
            )

            # Sign player
            signing = {
                'player_id': fa['player_id'],
                'player_name': fa['player_name'],
                'team_id': team_id,
                'team_name': team_name,
                'position': fa['position'],
                'overall': fa['overall'],
                'contract_aav': modified_contract['aav'],
                'contract_years': modified_contract['years'],
                'day_signed': day
            }

            all_signings.append(signing)
            available_fas.remove(fa)
            signings_today += 1

    return all_signings


def analyze_signings_by_archetype(
    all_team_signings: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Dict[str, Any]]:
    """
    Analyze signing patterns by GM archetype.

    Args:
        all_team_signings: Dict mapping archetype to list of signings

    Returns:
        Dict with analysis results per archetype
    """
    results = {}

    for archetype, signings in all_team_signings.items():
        if not signings:
            results[archetype] = {
                'count': 0,
                'avg_aav': 0,
                'avg_years': 0,
                'elite_signings': 0,
                'total_spent': 0
            }
            continue

        aavs = [s['contract_aav'] for s in signings]
        years = [s['contract_years'] for s in signings]
        elite_count = len([s for s in signings if s['overall'] >= 90])

        results[archetype] = {
            'count': len(signings),
            'avg_aav': sum(aavs) / len(aavs) if aavs else 0,
            'avg_years': sum(years) / len(years) if years else 0,
            'min_aav': min(aavs) if aavs else 0,
            'max_aav': max(aavs) if aavs else 0,
            'elite_signings': elite_count,
            'total_spent': sum(aavs),
            'signings': signings
        }

    return results


def validate_criteria(analysis: Dict[str, Dict[str, Any]]) -> Dict[str, bool]:
    """
    Validate that GM personalities create measurable differences.

    Args:
        analysis: Analysis results by archetype

    Returns:
        Dict with pass/fail status for each criterion
    """
    results = {}

    # Criterion 1: Win-Now pays ≥15% more than Rebuilder
    win_now_aav = analysis.get('Win-Now', {}).get('avg_aav', 0)
    rebuilder_aav = analysis.get('Rebuilder', {}).get('avg_aav', 0)

    if rebuilder_aav > 0:
        premium_pct = ((win_now_aav - rebuilder_aav) / rebuilder_aav) * 100
        results['win_now_premium'] = {
            'pass': premium_pct >= 15.0,
            'actual': premium_pct,
            'expected': 15.0,
            'message': f'Win-Now pays {premium_pct:.1f}% more than Rebuilder'
        }
    else:
        results['win_now_premium'] = {
            'pass': False,
            'actual': 0,
            'expected': 15.0,
            'message': 'No Rebuilder signings to compare'
        }

    # Criterion 2: Star Chasers pay more for elite players
    star_chaser_signings = analysis.get('Star Chaser', {}).get('signings', [])
    star_chaser_elite_aav = sum(s['contract_aav'] for s in star_chaser_signings if s['overall'] >= 90) / max(len([s for s in star_chaser_signings if s['overall'] >= 90]), 1)

    balanced_signings = analysis.get('Balanced', {}).get('signings', [])
    balanced_elite_aav = sum(s['contract_aav'] for s in balanced_signings if s['overall'] >= 90) / max(len([s for s in balanced_signings if s['overall'] >= 90]), 1)

    results['star_chaser_elite_premium'] = {
        'pass': star_chaser_elite_aav > balanced_elite_aav,
        'actual': star_chaser_elite_aav,
        'expected': balanced_elite_aav,
        'message': f'Star Chasers pay ${star_chaser_elite_aav:,.0f} for elite players vs Balanced ${balanced_elite_aav:,.0f}'
    }

    # Criterion 3: Conservative teams pay less overall than Win-Now
    conservative_aav = analysis.get('Conservative', {}).get('avg_aav', 0)
    win_now_aav = analysis.get('Win-Now', {}).get('avg_aav', 0)

    if win_now_aav > 0:
        conservative_discount_pct = ((win_now_aav - conservative_aav) / win_now_aav) * 100
        results['conservative_discount'] = {
            'pass': conservative_discount_pct >= 10.0,  # At least 10% less
            'actual': conservative_discount_pct,
            'expected': 10.0,
            'message': f'Conservative pays {conservative_discount_pct:.1f}% less than Win-Now'
        }
    else:
        results['conservative_discount'] = {
            'pass': False,
            'actual': 0,
            'expected': 10.0,
            'message': 'No Win-Now signings to compare'
        }

    return results


def print_validation_report(
    analysis: Dict[str, Dict[str, Any]],
    validation_results: Dict[str, bool]
):
    """
    Print comprehensive validation report to console.

    Args:
        analysis: Analysis results by archetype
        validation_results: Validation pass/fail results
    """
    print("=" * 80)
    print("FREE AGENCY GM BEHAVIOR VALIDATION")
    print("=" * 80)

    # Archetype summaries
    print("\n📊 SIGNING ANALYSIS BY GM ARCHETYPE")
    print("-" * 80)

    for archetype, stats in sorted(analysis.items()):
        print(f"\n{archetype} GMs:")
        print(f"  Total Signings:   {stats['count']}")
        print(f"  Avg AAV:          ${stats['avg_aav']:,.0f}")
        print(f"  Avg Years:        {stats['avg_years']:.1f}")
        print(f"  Elite Signings:   {stats['elite_signings']} (90+ OVR)")
        print(f"  Total Spent:      ${stats['total_spent']:,.0f}")
        if stats['count'] > 0:
            print(f"  AAV Range:        ${stats['min_aav']:,.0f} - ${stats['max_aav']:,.0f}")

    # Validation criteria
    print("\n" + "=" * 80)
    print("VALIDATION CRITERIA")
    print("=" * 80)

    all_passed = True
    for criterion, result in validation_results.items():
        status = "✅" if result['pass'] else "❌"
        print(f"{status} {result['message']}")
        if not result['pass']:
            all_passed = False

    # Overall verdict
    print("\n" + "=" * 80)
    if all_passed:
        print("VALIDATION RESULT: ALL CRITERIA PASSED ✅")
    else:
        print("VALIDATION RESULT: SOME CRITERIA FAILED ❌")
    print("=" * 80)


def run_validation():
    """Run multi-team FA simulation and validate GM behavior."""
    print("=" * 80)
    print("FREE AGENCY GM BEHAVIOR VALIDATION")
    print("=" * 80)

    # Create FA pool
    base_fa_pool = create_mock_fa_pool()
    print(f"\n📋 Created FA pool with {len(base_fa_pool)} players")
    print(f"   - Elite (90+ OVR): {len([p for p in base_fa_pool if p['overall'] >= 90])}")
    print(f"   - Starters (75-85 OVR): {len([p for p in base_fa_pool if 75 <= p['overall'] < 90])}")
    print(f"   - Depth (65-75 OVR): {len([p for p in base_fa_pool if p['overall'] < 75])}")

    # Define test teams
    test_teams = create_test_teams()
    print(f"\n🏈 Simulating free agency for {len(test_teams)} teams...")

    # Simulate FA for each team (each gets independent copy of FA pool)
    signings_by_archetype = defaultdict(list)

    for team in test_teams:
        print(f"   Simulating {team['name']} ({team['archetype']})...")

        # Give each team a fresh copy of the FA pool
        team_fa_pool = [fa.copy() for fa in base_fa_pool]

        signings = simulate_team_fa_period(
            team_id=team['team_id'],
            team_name=team['name'],
            archetype_name=team['archetype'],
            fa_pool=team_fa_pool
        )

        signings_by_archetype[team['archetype']].extend(signings)

    # Analyze results
    print("\n📈 Analyzing signing patterns...")
    analysis = analyze_signings_by_archetype(dict(signings_by_archetype))

    # Validate criteria
    validation_results = validate_criteria(analysis)

    # Print report
    print_validation_report(analysis, validation_results)


if __name__ == "__main__":
    run_validation()
