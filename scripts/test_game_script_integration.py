#!/usr/bin/env python3
"""
Diagnostic script to verify game script integration is working.

Tests that:
1. raw_game_state with score_differential is correctly analyzed
2. GameSituationAnalyzer returns correct game script
3. OffensiveCoordinator applies correct run/pass ratios

Run: PYTHONPATH=src python scripts/test_game_script_integration.py
"""

from play_engine.play_calling.game_situation_analyzer import (
    GameSituationAnalyzer, GameScript, GamePhase
)
from play_engine.play_calling.offensive_coordinator import (
    OffensiveCoordinator, OffensivePhilosophy, SituationalCalling
)


def test_scenario(name: str, score_diff: int, quarter: int, time_remaining: int):
    """Test a specific game scenario."""
    print(f"\n{'='*60}")
    print(f"SCENARIO: {name}")
    print(f"  Score Differential: {score_diff:+d} (possessing team perspective)")
    print(f"  Quarter: {quarter}, Time: {time_remaining // 60}:{time_remaining % 60:02d}")

    # Build raw_game_state (simulates what game_loop_controller builds)
    raw_game_state = {
        'home_score': 13 if score_diff > 0 else 0,
        'away_score': 0 if score_diff > 0 else 13,
        'quarter': quarter,
        'time_remaining': time_remaining,
        'possessing_team_id': 1,
        'home_team_id': 1,
        'away_team_id': 2,
        'score_differential': score_diff,  # THE KEY FIELD
        'field_position': 50,
        'down': 1,
        'yards_to_go': 10,
    }

    # Analyze game context
    game_context = GameSituationAnalyzer.analyze_game_context(raw_game_state)

    print(f"\n  RESULT:")
    print(f"    Game Phase: {game_context.game_phase.name}")
    print(f"    Game Script: {game_context.game_script.name}")

    # Create OC with high adherence to see the effect
    oc = OffensiveCoordinator(
        name="Test OC",
        game_script_adherence=0.9,  # High adherence to see script effect
        philosophy=OffensivePhilosophy(),
        situational_calling=SituationalCalling()
    )

    # Get play concepts with game context
    context = {'game_context': game_context}
    concepts = oc.get_play_concept_preference('first_down', context)

    # Calculate run vs pass weight totals
    run_concepts = ['power', 'sweep', 'off_tackle', 'counter', 'draw', 'inside_zone', 'outside_zone']
    pass_concepts = ['slants', 'quick_out', 'comeback', 'four_verticals', 'mesh', 'sail', 'deep_crosser']

    run_weight = sum(concepts.get(c, 0) for c in run_concepts)
    pass_weight = sum(concepts.get(c, 0) for c in pass_concepts)
    total = run_weight + pass_weight

    if total > 0:
        run_pct = run_weight / total * 100
        pass_pct = pass_weight / total * 100
        print(f"    Run/Pass Tendency: {run_pct:.0f}% run / {pass_pct:.0f}% pass")
    else:
        print(f"    Run/Pass Tendency: Unable to calculate (no concepts)")

    # Verify expected script
    return game_context.game_script


def main():
    print("=" * 60)
    print("GAME SCRIPT INTEGRATION TEST")
    print("=" * 60)
    print("\nThis tests the full path:")
    print("  raw_game_state -> GameSituationAnalyzer -> GameContext -> OC decisions")

    # Test scenarios
    results = []

    # Scenario 1: Browns winning 13-0 in Q4 (should be CONTROL_GAME or PROTECT_LEAD)
    script = test_scenario(
        "Browns winning 13-0 in Q4 (like the CLE vs CIN game)",
        score_diff=13, quarter=4, time_remaining=31
    )
    results.append(("13-0 lead Q4", script, script in [GameScript.CONTROL_GAME, GameScript.PROTECT_LEAD]))

    # Scenario 2: Tied game Q3 (should be COMPETITIVE)
    script = test_scenario(
        "Tied game in Q3",
        score_diff=0, quarter=3, time_remaining=600
    )
    results.append(("Tied Q3", script, script == GameScript.COMPETITIVE))

    # Scenario 3: Down 21 in Q4 (should be DESPERATION)
    script = test_scenario(
        "Down 21 in Q4 - trailing badly",
        score_diff=-21, quarter=4, time_remaining=300
    )
    results.append(("Down 21 Q4", script, script == GameScript.DESPERATION))

    # Scenario 4: Up 3 in Q4 (should be PROTECT_LEAD)
    script = test_scenario(
        "Up 3 in Q4 - protecting small lead",
        score_diff=3, quarter=4, time_remaining=120
    )
    results.append(("Up 3 Q4", script, script == GameScript.PROTECT_LEAD))

    # Scenario 5: Down 7 in Q4 (still COMPETITIVE with 5 min left)
    # COMEBACK_MODE requires -10+ in FOURTH_QUARTER_LATE, or -3+ in TWO_MINUTE_WARNING
    script = test_scenario(
        "Down 7 in Q4 - still competitive",
        score_diff=-7, quarter=4, time_remaining=300
    )
    results.append(("Down 7 Q4", script, script == GameScript.COMPETITIVE))

    # Scenario 6: Down 10 in Q4 (should be COMEBACK_MODE)
    script = test_scenario(
        "Down 10 in Q4 - need to catch up",
        score_diff=-10, quarter=4, time_remaining=300
    )
    results.append(("Down 10 Q4", script, script == GameScript.COMEBACK_MODE))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    all_pass = True
    for name, script, passed in results:
        status = "PASS" if passed else "FAIL"
        all_pass = all_pass and passed
        print(f"  [{status}] {name}: {script.name}")

    print("\n" + "=" * 60)
    if all_pass:
        print("ALL TESTS PASSED - Game script integration is working!")
    else:
        print("SOME TESTS FAILED - Check the game script logic")
    print("=" * 60)

    return 0 if all_pass else 1


if __name__ == "__main__":
    exit(main())
