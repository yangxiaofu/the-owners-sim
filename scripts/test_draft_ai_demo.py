"""
Draft AI Demo Script

Demonstrates the needs-based draft AI with realistic scenarios.

Run this to see:
- How AI teams evaluate prospects based on positional needs
- Need-based bonuses in action (CRITICAL +15, HIGH +8, MEDIUM +3)
- Best available player selection
- Draft results with detailed explanations

Usage:
    python scripts/test_draft_ai_demo.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from offseason.draft_manager import DraftManager


def create_mock_prospects():
    """Create realistic mock prospects for testing."""
    return [
        # Elite QB (projected #1 overall)
        {
            'player_id': 'prospect_1',
            'first_name': 'Caleb',
            'last_name': 'Williams',
            'position': 'quarterback',
            'overall': 92,
            'college': 'USC',
            'projected_pick_min': 1,
            'projected_pick_max': 5,
            'age': 21
        },
        # Elite Edge Rusher (projected top 5)
        {
            'player_id': 'prospect_2',
            'first_name': 'Jared',
            'last_name': 'Verse',
            'position': 'defensive_end',
            'overall': 90,
            'college': 'Florida State',
            'projected_pick_min': 3,
            'projected_pick_max': 8,
            'age': 22
        },
        # Top WR (projected top 10)
        {
            'player_id': 'prospect_3',
            'first_name': 'Marvin',
            'last_name': 'Harrison Jr',
            'position': 'wide_receiver',
            'overall': 91,
            'college': 'Ohio State',
            'projected_pick_min': 4,
            'projected_pick_max': 10,
            'age': 21
        },
        # Elite LT (projected top 5)
        {
            'player_id': 'prospect_4',
            'first_name': 'Joe',
            'last_name': 'Alt',
            'position': 'left_tackle',
            'overall': 89,
            'college': 'Notre Dame',
            'projected_pick_min': 2,
            'projected_pick_max': 7,
            'age': 22
        },
        # CB (projected 10-15)
        {
            'player_id': 'prospect_5',
            'first_name': 'Quinyon',
            'last_name': 'Mitchell',
            'position': 'cornerback',
            'overall': 85,
            'college': 'Toledo',
            'projected_pick_min': 10,
            'projected_pick_max': 20,
            'age': 21
        },
        # RB (projected 15-25)
        {
            'player_id': 'prospect_6',
            'first_name': 'Jonathon',
            'last_name': 'Brooks',
            'position': 'running_back',
            'overall': 83,
            'college': 'Texas',
            'projected_pick_min': 15,
            'projected_pick_max': 30,
            'age': 20
        },
        # LB (projected 20-30)
        {
            'player_id': 'prospect_7',
            'first_name': 'Edgerrin',
            'last_name': 'Cooper',
            'position': 'linebacker',
            'overall': 82,
            'college': 'Texas A&M',
            'projected_pick_min': 20,
            'projected_pick_max': 35,
            'age': 22
        },
        # TE (projected 25-35)
        {
            'player_id': 'prospect_8',
            'first_name': 'Brock',
            'last_name': 'Bowers',
            'position': 'tight_end',
            'overall': 88,
            'college': 'Georgia',
            'projected_pick_min': 10,
            'projected_pick_max': 20,
            'age': 21
        },
        # Safety (projected 30-40)
        {
            'player_id': 'prospect_9',
            'first_name': 'Cooper',
            'last_name': 'DeJean',
            'position': 'safety',
            'overall': 81,
            'college': 'Iowa',
            'projected_pick_min': 25,
            'projected_pick_max': 40,
            'age': 22
        },
        # DT (projected 20-30)
        {
            'player_id': 'prospect_10',
            'first_name': 'Byron',
            'last_name': 'Murphy',
            'position': 'defensive_tackle',
            'overall': 84,
            'college': 'Texas',
            'projected_pick_min': 18,
            'projected_pick_max': 30,
            'age': 21
        }
    ]


def create_test_scenarios():
    """Create test scenarios showing different need situations."""
    return [
        {
            'name': 'Scenario 1: QB-Needy Team (Pick #1)',
            'team_id': 1,
            'pick_position': 1,
            'team_needs': [
                {'position': 'quarterback', 'urgency_score': 5, 'urgency': 'CRITICAL'},
                {'position': 'left_tackle', 'urgency_score': 4, 'urgency': 'HIGH'},
                {'position': 'wide_receiver', 'urgency_score': 3, 'urgency': 'MEDIUM'}
            ],
            'expected_pick': 'Caleb Williams (QB) - CRITICAL need + best prospect',
            'explanation': 'QB need is CRITICAL (+15 bonus), Williams is elite (92 OVR)'
        },
        {
            'name': 'Scenario 2: Team with OL Need (Pick #2)',
            'team_id': 2,
            'pick_position': 2,
            'team_needs': [
                {'position': 'left_tackle', 'urgency_score': 5, 'urgency': 'CRITICAL'},
                {'position': 'cornerback', 'urgency_score': 4, 'urgency': 'HIGH'},
                {'position': 'linebacker', 'urgency_score': 3, 'urgency': 'MEDIUM'}
            ],
            'expected_pick': 'Joe Alt (LT) - CRITICAL OL need',
            'explanation': 'LT is CRITICAL need (+15 bonus), Alt gets 89 + 15 = 104 score'
        },
        {
            'name': 'Scenario 3: Best Available (Pick #3)',
            'team_id': 3,
            'pick_position': 3,
            'team_needs': [
                {'position': 'linebacker', 'urgency_score': 3, 'urgency': 'MEDIUM'},
                {'position': 'safety', 'urgency_score': 3, 'urgency': 'MEDIUM'},
                {'position': 'running_back', 'urgency_score': 2, 'urgency': 'LOW'}
            ],
            'expected_pick': 'Marvin Harrison Jr (WR) or Jared Verse (EDGE)',
            'explanation': 'No critical needs, so picks best available prospect'
        },
        {
            'name': 'Scenario 4: WR-Needy Team (Pick #4)',
            'team_id': 4,
            'pick_position': 4,
            'team_needs': [
                {'position': 'wide_receiver', 'urgency_score': 5, 'urgency': 'CRITICAL'},
                {'position': 'defensive_end', 'urgency_score': 4, 'urgency': 'HIGH'},
                {'position': 'cornerback', 'urgency_score': 3, 'urgency': 'MEDIUM'}
            ],
            'expected_pick': 'Marvin Harrison Jr (WR) - CRITICAL WR need',
            'explanation': 'WR is CRITICAL (+15), Harrison Jr gets 91 + 15 = 106 score'
        },
        {
            'name': 'Scenario 5: Defensive Team (Pick #5)',
            'team_id': 5,
            'pick_position': 5,
            'team_needs': [
                {'position': 'defensive_end', 'urgency_score': 5, 'urgency': 'CRITICAL'},
                {'position': 'cornerback', 'urgency_score': 5, 'urgency': 'CRITICAL'},
                {'position': 'linebacker', 'urgency_score': 4, 'urgency': 'HIGH'}
            ],
            'expected_pick': 'Jared Verse (EDGE) - CRITICAL pass rush need',
            'explanation': 'EDGE is CRITICAL (+15), Verse gets 90 + 15 = 105 score'
        }
    ]


def run_scenario_test(draft_manager, scenario, available_prospects):
    """
    Run a single draft scenario and show evaluation.

    Args:
        draft_manager: DraftManager instance
        scenario: Test scenario dict
        available_prospects: List of available prospects

    Returns:
        Selected prospect dict
    """
    print("\n" + "=" * 80)
    print(f"🏈 {scenario['name']}")
    print("=" * 80)

    # Show team needs
    print(f"\n📋 Team {scenario['team_id']} Needs (Pick #{scenario['pick_position']}):")
    for need in scenario['team_needs']:
        print(f"   {need['urgency']:10} - {need['position']:20} (urgency: {need['urgency_score']})")

    print(f"\n💡 Expected: {scenario['expected_pick']}")
    print(f"   Why: {scenario['explanation']}")

    # Evaluate all prospects
    print(f"\n🔍 Evaluating Top Prospects:")
    print(f"{'Prospect':<30} {'Pos':<6} {'OVR':<5} {'Need Bonus':<12} {'Final Score':<12}")
    print("-" * 80)

    evaluations = []
    for prospect in available_prospects:
        score = draft_manager._evaluate_prospect(
            prospect=prospect,
            team_needs=scenario['team_needs'],
            pick_position=scenario['pick_position']
        )

        # Calculate need bonus for display
        need_bonus = 0
        for need in scenario['team_needs']:
            if need['position'] == prospect['position']:
                if need['urgency_score'] >= 5:
                    need_bonus = 15
                elif need['urgency_score'] >= 4:
                    need_bonus = 8
                elif need['urgency_score'] >= 3:
                    need_bonus = 3
                break

        evaluations.append({
            'prospect': prospect,
            'score': score,
            'need_bonus': need_bonus
        })

        name = f"{prospect['first_name']} {prospect['last_name']}"
        need_str = f"+{need_bonus}" if need_bonus > 0 else "0"
        print(f"{name:<30} {prospect['position']:<6} {prospect['overall']:<5} {need_str:<12} {score:<12.1f}")

    # Sort by score and pick best
    evaluations.sort(key=lambda x: x['score'], reverse=True)
    best = evaluations[0]

    print(f"\n✅ AI SELECTS: {best['prospect']['first_name']} {best['prospect']['last_name']} "
          f"({best['prospect']['position']}, {best['prospect']['overall']} OVR) "
          f"[Score: {best['score']:.1f}]")

    # Remove from available pool
    selected_id = best['prospect']['player_id']
    return best['prospect'], [p for p in available_prospects if p['player_id'] != selected_id]


def main():
    """Run comprehensive draft AI test scenarios."""
    print("\n" + "=" * 80)
    print("🏈 NFL DRAFT AI - NEEDS-BASED SELECTION TEST")
    print("=" * 80)
    print("\nThis test demonstrates how the draft AI evaluates prospects using:")
    print("  • Base Value: Prospect overall rating")
    print("  • CRITICAL Need Bonus: +15 points (urgency score 5)")
    print("  • HIGH Need Bonus: +8 points (urgency score 4)")
    print("  • MEDIUM Need Bonus: +3 points (urgency score 3)")
    print("  • Reach Penalty: -5 points (if drafting >20 picks above projection)")

    # Create DraftManager (in-memory, no persistence)
    draft_manager = DraftManager(
        database_path=":memory:",
        dynasty_id="draft_ai_test",
        season_year=2025,
        enable_persistence=False
    )

    # Create mock prospects
    available_prospects = create_mock_prospects()

    print(f"\n📚 Draft Class: {len(available_prospects)} prospects available")
    print("\nTop Prospects:")
    for i, p in enumerate(sorted(available_prospects, key=lambda x: x['overall'], reverse=True)[:5], 1):
        print(f"  {i}. {p['first_name']} {p['last_name']} - {p['position']} ({p['overall']} OVR)")

    # Run test scenarios
    scenarios = create_test_scenarios()
    results = []

    for scenario in scenarios:
        selected, available_prospects = run_scenario_test(
            draft_manager,
            scenario,
            available_prospects
        )
        results.append({
            'scenario': scenario['name'],
            'team_id': scenario['team_id'],
            'pick': scenario['pick_position'],
            'selected': f"{selected['first_name']} {selected['last_name']}",
            'position': selected['position'],
            'overall': selected['overall']
        })

    # Summary
    print("\n" + "=" * 80)
    print("📊 DRAFT SUMMARY")
    print("=" * 80)
    print(f"{'Pick':<6} {'Team':<6} {'Player':<25} {'Pos':<8} {'OVR':<5}")
    print("-" * 80)
    for r in results:
        print(f"{r['pick']:<6} {r['team_id']:<6} {r['selected']:<25} {r['position']:<8} {r['overall']:<5}")

    print("\n" + "=" * 80)
    print("✅ TEST COMPLETE")
    print("=" * 80)
    print("\nKey Observations:")
    print("  ✓ CRITICAL needs get +15 bonus, often determining picks")
    print("  ✓ HIGH needs get +8 bonus, can swing close decisions")
    print("  ✓ When no critical needs exist, AI picks best available")
    print("  ✓ Position matching is exact (quarterback != wide_receiver)")
    print("  ✓ Need bonuses can overcome lower overall ratings")
    print("\n💡 This is Phase 2A (Core AI). Phase 2B will add GM personalities!")
    print("   (e.g., Risk-tolerant GMs prefer high-ceiling prospects,")
    print("    Win-Now GMs prefer polished rookies, etc.)")
    print()


if __name__ == "__main__":
    main()
