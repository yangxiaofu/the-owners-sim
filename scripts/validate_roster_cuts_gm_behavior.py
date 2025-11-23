#!/usr/bin/env python3
"""
Roster Cuts GM Behavior Validation Script

Creates 5 GM archetypes and validates they create statistically significant
differences in roster cut decisions when evaluating the same 90-man roster.

Usage:
    python scripts/validate_roster_cuts_gm_behavior.py
"""

import sys
import os
from typing import List, Dict, Any
from dataclasses import dataclass
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from offseason.roster_manager import RosterManager
from team_management.gm_archetype import GMArchetype
from transactions.personality_modifiers import TeamContext


@dataclass
class RosterMetrics:
    """Metrics for a final 53-man roster"""
    gm_name: str
    long_tenured_pct: float  # % with 5+ years tenure
    expensive_pct: float  # % with >$5M cap hit
    avg_age: float
    veteran_pct: float  # % 30+ years old
    total_cap_hit: float
    final_roster_size: int


def create_gm_archetypes() -> List[GMArchetype]:
    """
    Create 5 distinct GM archetypes for testing.

    Returns:
        List of 5 GMArchetype objects
    """
    return [
        GMArchetype(
            name="Loyal",
            description="Loyal GM who values team veterans",
            loyalty=0.9,
            cap_management=0.3,
            veteran_preference=0.7
        ),
        GMArchetype(
            name="Ruthless",
            description="Ruthless GM who makes cold business decisions",
            loyalty=0.1,
            cap_management=0.9,
            veteran_preference=0.2
        ),
        GMArchetype(
            name="Cap-Conscious",
            description="Cap-focused GM who prioritizes financial efficiency",
            loyalty=0.5,
            cap_management=0.95,
            veteran_preference=0.5
        ),
        GMArchetype(
            name="Veteran-Pref",
            description="GM who strongly prefers experienced veterans",
            loyalty=0.7,
            cap_management=0.5,
            veteran_preference=0.9
        ),
        GMArchetype(
            name="Youth-Focused",
            description="GM who builds around young talent",
            loyalty=0.3,
            cap_management=0.5,
            veteran_preference=0.1
        ),
    ]


def generate_90_man_roster() -> List[Dict[str, Any]]:
    """
    Generate a realistic 90-man roster with diverse characteristics.

    Returns:
        List of 90 player dicts
    """
    import random

    roster = []
    player_id = 1

    # Position distribution (approximate NFL 90-man roster)
    position_counts = {
        # Offense (~45)
        'quarterback': 4,
        'running_back': 7,
        'wide_receiver': 11,
        'tight_end': 5,
        'left_tackle': 4,
        'right_tackle': 3,
        'left_guard': 3,
        'right_guard': 3,
        'center': 3,

        # Defense (~40)
        'defensive_end': 7,
        'defensive_tackle': 6,
        'linebacker': 12,
        'cornerback': 10,
        'safety': 7,

        # Special Teams
        'kicker': 2,
        'punter': 2,
    }

    for position, count in position_counts.items():
        for i in range(count):
            # Realistic age distribution (21-33, weighted toward younger)
            age_weights = [
                (21, 10), (22, 15), (23, 20), (24, 25), (25, 30),
                (26, 25), (27, 20), (28, 15), (29, 10), (30, 8),
                (31, 5), (32, 3), (33, 2)
            ]
            age = random.choices(
                [age for age, _ in age_weights],
                weights=[weight for _, weight in age_weights],
                k=1
            )[0]

            # Tenure based on age (realistic: can't have 10 years tenure at age 22)
            max_tenure = min(age - 21, 12)
            tenure = random.randint(0, max_tenure)

            # Calculate joined_date based on tenure (2024 - tenure years)
            joined_year = 2024 - tenure
            joined_date = f"{joined_year}-03-15"  # Arbitrary March 15th

            # Cap hit distribution (realistic NFL contracts)
            cap_hit_ranges = [
                (500_000, 1_000_000, 40),  # Rookies/practice squad level
                (1_000_000, 2_000_000, 30),  # Depth players
                (2_000_000, 5_000_000, 15),  # Solid backups/rotational
                (5_000_000, 10_000_000, 10),  # Starters
                (10_000_000, 15_000_000, 5),  # Stars
            ]
            cap_range = random.choices(
                cap_hit_ranges,
                weights=[weight for _, _, weight in cap_hit_ranges],
                k=1
            )[0]
            cap_hit = random.randint(cap_range[0], cap_range[1])

            # Overall rating (60-95, realistic NFL range)
            # Correlated with cap hit somewhat
            if cap_hit > 10_000_000:
                overall = random.randint(85, 95)
            elif cap_hit > 5_000_000:
                overall = random.randint(75, 88)
            elif cap_hit > 2_000_000:
                overall = random.randint(68, 80)
            else:
                overall = random.randint(60, 75)

            player = {
                'player_id': player_id,
                'player_name': f"{position.upper()}{i+1}",
                'position': position,
                'overall': overall,
                'age': age,
                'team_years_tenure': tenure,
                'joined_date': joined_date,  # Required for years_with_team calculation
                'cap_hit': cap_hit,
            }

            roster.append(player)
            player_id += 1

    return roster


def calculate_roster_metrics(gm_name: str, roster: List[Dict[str, Any]]) -> RosterMetrics:
    """
    Calculate metrics for a final roster.

    Args:
        gm_name: Name of GM archetype
        roster: List of player dicts in final 53-man roster

    Returns:
        RosterMetrics object
    """
    if not roster:
        return RosterMetrics(
            gm_name=gm_name,
            long_tenured_pct=0.0,
            expensive_pct=0.0,
            avg_age=0.0,
            veteran_pct=0.0,
            total_cap_hit=0.0,
            final_roster_size=0
        )

    # Long-tenured %
    long_tenured_count = sum(1 for p in roster if p.get('team_years_tenure', 0) >= 5)
    long_tenured_pct = (long_tenured_count / len(roster)) * 100

    # Expensive player %
    expensive_count = sum(1 for p in roster if p.get('cap_hit', 0) > 5_000_000)
    expensive_pct = (expensive_count / len(roster)) * 100

    # Average age
    avg_age = sum(p.get('age', 0) for p in roster) / len(roster)

    # Veteran %
    veteran_count = sum(1 for p in roster if p.get('age', 0) >= 30)
    veteran_pct = (veteran_count / len(roster)) * 100

    # Total cap hit
    total_cap_hit = sum(p.get('cap_hit', 0) for p in roster)

    return RosterMetrics(
        gm_name=gm_name,
        long_tenured_pct=long_tenured_pct,
        expensive_pct=expensive_pct,
        avg_age=avg_age,
        veteran_pct=veteran_pct,
        total_cap_hit=total_cap_hit,
        final_roster_size=len(roster)
    )


def validate_success_criteria(metrics_list: List[RosterMetrics]) -> Dict[str, Any]:
    """
    Validate success criteria for GM behavior differences.

    Args:
        metrics_list: List of RosterMetrics for each GM

    Returns:
        Dict mapping criterion name to results
    """
    # Find metrics for each archetype
    metrics_by_name = {m.gm_name: m for m in metrics_list}

    loyal = metrics_by_name.get("Loyal")
    ruthless = metrics_by_name.get("Ruthless")
    cap_conscious = metrics_by_name.get("Cap-Conscious")
    veteran_pref = metrics_by_name.get("Veteran-Pref")
    youth_focused = metrics_by_name.get("Youth-Focused")

    results = {}

    # Criterion 1: Loyal keeps ≥20% more long-tenured than Ruthless
    if loyal and ruthless:
        loyal_long = loyal.long_tenured_pct
        ruthless_long = ruthless.long_tenured_pct
        variance_pct = ((loyal_long - ruthless_long) / ruthless_long * 100) if ruthless_long > 0 else 0
        results['loyal_vs_ruthless_tenure'] = {
            'passed': loyal_long >= ruthless_long * 1.20,
            'loyal_pct': loyal_long,
            'ruthless_pct': ruthless_long,
            'variance_pct': variance_pct
        }

    # Criterion 2: Cap-Conscious cuts ≥15% more expensive players than others
    if cap_conscious:
        other_expensive = [m.expensive_pct for m in metrics_list if m.gm_name != "Cap-Conscious"]
        avg_other_expensive = sum(other_expensive) / len(other_expensive) if other_expensive else 0
        cap_expensive = cap_conscious.expensive_pct
        variance_pct = ((avg_other_expensive - cap_expensive) / avg_other_expensive * 100) if avg_other_expensive > 0 else 0
        results['cap_conscious_cuts_expensive'] = {
            'passed': cap_expensive <= avg_other_expensive * 0.85,
            'cap_conscious_pct': cap_expensive,
            'avg_other_pct': avg_other_expensive,
            'variance_pct': variance_pct
        }

    # Criterion 3: Veteran-Pref has higher avg age than Youth-Focused
    if veteran_pref and youth_focused:
        vet_age = veteran_pref.avg_age
        youth_age = youth_focused.avg_age
        age_diff = vet_age - youth_age
        results['veteran_vs_youth_age'] = {
            'passed': vet_age > youth_age,
            'veteran_age': vet_age,
            'youth_age': youth_age,
            'age_diff': age_diff
        }

    # Criterion 4: Youth-Focused has lower avg age than Veteran-Pref (inverse of #3)
    if youth_focused and veteran_pref:
        youth_age = youth_focused.avg_age
        vet_age = veteran_pref.avg_age
        age_diff = vet_age - youth_age
        results['youth_vs_veteran_age'] = {
            'passed': youth_age < vet_age,
            'youth_age': youth_age,
            'veteran_age': vet_age,
            'age_diff': age_diff
        }

    return results


def print_report(metrics_list: List[RosterMetrics], criteria_results: Dict[str, Any]):
    """
    Print formatted validation report.

    Args:
        metrics_list: List of RosterMetrics for each GM
        criteria_results: Dict of validation criteria results
    """
    print("\n" + "=" * 100)
    print("📊 ROSTER CUTS GM BEHAVIOR VALIDATION")
    print("=" * 100)
    print()

    # Print metrics table
    print(f"{'GM Archetype':<18} {'Long-Tenure %':>15} {'Expensive %':>15} {'Avg Age':>10} {'Veteran %':>12} {'Total Cap Hit':>15}")
    print("-" * 100)

    for metrics in metrics_list:
        print(
            f"{metrics.gm_name:<18} "
            f"{metrics.long_tenured_pct:>14.1f}% "
            f"{metrics.expensive_pct:>14.1f}% "
            f"{metrics.avg_age:>10.1f} "
            f"{metrics.veteran_pct:>11.1f}% "
            f"${metrics.total_cap_hit/1_000_000:>13.1f}M"
        )

    print("-" * 100)
    print()

    # Print success criteria
    print("SUCCESS CRITERIA:")

    # Criterion 1
    if 'loyal_vs_ruthless_tenure' in criteria_results:
        result = criteria_results['loyal_vs_ruthless_tenure']
        status = "✅" if result['passed'] else "❌"
        print(
            f"{status} Loyal keeps ≥20% more long-tenured "
            f"({result['loyal_pct']:.1f}% vs {result['ruthless_pct']:.1f}% = "
            f"{result['variance_pct']:+.1f}% variance)"
        )

    # Criterion 2
    if 'cap_conscious_cuts_expensive' in criteria_results:
        result = criteria_results['cap_conscious_cuts_expensive']
        status = "✅" if result['passed'] else "❌"
        print(
            f"{status} Cap-Conscious cuts ≥15% more expensive "
            f"({result['cap_conscious_pct']:.1f}% vs {result['avg_other_pct']:.1f}% = "
            f"{result['variance_pct']:+.1f}% variance)"
        )

    # Criterion 3
    if 'veteran_vs_youth_age' in criteria_results:
        result = criteria_results['veteran_vs_youth_age']
        status = "✅" if result['passed'] else "❌"
        print(
            f"{status} Veteran-Pref avg age higher "
            f"({result['veteran_age']:.1f} vs {result['youth_age']:.1f} = "
            f"{result['age_diff']:+.1f} years)"
        )

    # Criterion 4
    if 'youth_vs_veteran_age' in criteria_results:
        result = criteria_results['youth_vs_veteran_age']
        status = "✅" if result['passed'] else "❌"
        print(
            f"{status} Youth-Focused avg age lower "
            f"({result['youth_age']:.1f} vs {result['veteran_age']:.1f} = "
            f"{result['age_diff']:+.1f} years)"
        )

    # Overall pass rate
    passed_count = sum(1 for r in criteria_results.values() if r.get('passed', False))
    total_count = len(criteria_results)
    pass_rate = (passed_count / total_count * 100) if total_count > 0 else 0

    print()
    if passed_count == total_count:
        print(f"✅ ALL CRITERIA PASSED ({passed_count}/{total_count} = {pass_rate:.0f}%)")
    else:
        print(f"⚠️  SOME CRITERIA FAILED ({passed_count}/{total_count} = {pass_rate:.0f}%)")
    print()


def run_validation():
    """
    Run the complete GM behavior validation.
    """
    print("Generating 90-man roster...")
    roster_90 = generate_90_man_roster()
    print(f"✓ Generated {len(roster_90)} players")
    print()

    # Create GM archetypes
    gm_archetypes = create_gm_archetypes()

    # Create mock team context (used for all GMs)
    mock_team_context = TeamContext(
        team_id=1,
        season=2024,
        wins=8,
        losses=9,
        cap_space=25_000_000,
        cap_percentage=0.15
    )

    metrics_list = []

    for gm in gm_archetypes:
        print(f"Running roster cuts for {gm.name} GM...")

        # Create RosterManager WITHOUT GM archetype (to avoid context service initialization)
        roster_manager = RosterManager(
            database_path=":memory:",
            dynasty_id="test_dynasty",
            season_year=2024,
            enable_persistence=False,
            gm_archetype=None  # Don't initialize context service
        )

        # Manually set GM archetype after initialization
        roster_manager.gm = gm

        # Mock the _get_mock_90_man_roster method to return our test roster
        import copy
        roster_copy = copy.deepcopy(roster_90)

        # Mock both _get_mock_90_man_roster and context service
        with patch.object(roster_manager, '_get_mock_90_man_roster', return_value=roster_copy):
            # Mock the context service's build_team_context method
            mock_context_service = Mock()
            mock_context_service.build_team_context.return_value = mock_team_context
            roster_manager.context_service = mock_context_service

            # Run roster cuts
            result = roster_manager.finalize_53_man_roster_ai(team_id=1, gm_archetype=gm)

        final_roster = result.get('final_roster', [])
        cuts = result.get('cuts', [])

        print(f"  ✓ Final roster: {len(final_roster)} players")
        print(f"  ✓ Cuts: {len(cuts)} players")

        # Calculate metrics
        metrics = calculate_roster_metrics(gm.name, final_roster)
        metrics_list.append(metrics)
        print()

    # Validate success criteria
    criteria_results = validate_success_criteria(metrics_list)

    # Print report
    print_report(metrics_list, criteria_results)


if __name__ == "__main__":
    run_validation()
