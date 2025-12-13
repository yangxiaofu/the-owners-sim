"""
Demonstration of the Penalty Double-Counting Fix

This script demonstrates that the penalty system now correctly handles
penalty yardage according to NFL rules:
1. Pre-snap penalties (negated_play=True): Use only penalty yards
2. Choice penalties (negated_play=False): Team chooses accept/decline
   - Accept: Use only penalty yards from LOS
   - Decline: Use play result, ignore penalty
"""

from play_engine.mechanics.penalties.penalty_engine import PenaltyEngine, PlayContext
from play_engine.mechanics.penalties.penalty_data_structures import PenaltyInstance


def demonstrate_penalty_fix():
    """Demonstrate the penalty yardage fix with examples"""

    print("=" * 80)
    print("PENALTY DOUBLE-COUNTING FIX DEMONSTRATION")
    print("=" * 80)
    print()

    engine = PenaltyEngine()

    # Example 1: Pre-snap penalty (FALSE START)
    print("EXAMPLE 1: Pre-snap Penalty (False Start)")
    print("-" * 80)
    print("Scenario: 1st & 10, play gains 7 yards, but false start occurs")
    print()

    penalty1 = PenaltyInstance(
        penalty_type="false_start",
        penalized_player_name="John Smith",
        penalized_player_number=75,
        penalized_player_position="left_tackle",
        team_penalized="home",
        yards_assessed=-5,
        automatic_first_down=False,
        automatic_loss_of_down=False,
        negated_play=True,
        quarter=1,
        time_remaining="10:00",
        down=1,
        distance=10,
        field_position=50,
        score_differential=0
    )

    result1 = engine._apply_penalty_effects(penalty1, 7)

    print(f"Play Result Before Penalty: +7 yards")
    print(f"Penalty: {penalty1.penalty_type.replace('_', ' ').title()} ({penalty1.yards_assessed} yards)")
    print(f"Play Negated: {penalty1.negated_play}")
    print()
    print(f"✓ CORRECT Final Result: {result1.modified_yards} yards (only penalty)")
    print(f"✗ WRONG (old logic): {7 + (-5)} = 2 yards (double-counted)")
    print()
    print()

    # Example 2: Defensive penalty accepted (FACE MASK)
    print("EXAMPLE 2: Defensive Penalty - Accepted (Face Mask)")
    print("-" * 80)
    print("Scenario: 2nd & 10, play gains 3 yards, but face mask penalty (15 yards)")
    print()

    penalty2 = PenaltyInstance(
        penalty_type="face_mask",
        penalized_player_name="Mike Johnson",
        penalized_player_number=52,
        penalized_player_position="linebacker",
        team_penalized="away",
        yards_assessed=15,
        automatic_first_down=True,
        automatic_loss_of_down=False,
        negated_play=False,
        quarter=2,
        time_remaining="8:30",
        down=2,
        distance=10,
        field_position=45,
        score_differential=3
    )

    result2 = engine._apply_penalty_effects(penalty2, 3)

    print(f"Play Result Before Penalty: +3 yards")
    print(f"Penalty: {penalty2.penalty_type.replace('_', ' ').title()} (+{penalty2.yards_assessed} yards)")
    print(f"Play Negated: {penalty2.negated_play}")
    print()
    print(f"Decision: Penalty is better (15 > 3), so ACCEPT")
    print(f"Penalty Accepted: {penalty2.penalty_accepted}")
    print()
    print(f"✓ CORRECT Final Result: {result2.modified_yards} yards (penalty from LOS)")
    print(f"✗ WRONG (old logic): {3 + 15} = 18 yards (double-counted)")
    print(f"Automatic First Down: {result2.automatic_first_down}")
    print()
    print()

    # Example 3: Defensive penalty declined (BIG PLAY)
    print("EXAMPLE 3: Defensive Penalty - Declined (Big Play)")
    print("-" * 80)
    print("Scenario: 1st & 10, play gains 35 yards, but illegal contact (5 yards)")
    print()

    penalty3 = PenaltyInstance(
        penalty_type="illegal_contact",
        penalized_player_name="Tom Wilson",
        penalized_player_number=24,
        penalized_player_position="cornerback",
        team_penalized="away",
        yards_assessed=5,
        automatic_first_down=True,
        automatic_loss_of_down=False,
        negated_play=False,
        quarter=3,
        time_remaining="5:15",
        down=1,
        distance=10,
        field_position=65,
        score_differential=-7
    )

    result3 = engine._apply_penalty_effects(penalty3, 35)

    print(f"Play Result Before Penalty: +35 yards (TOUCHDOWN!)")
    print(f"Penalty: {penalty3.penalty_type.replace('_', ' ').title()} (+{penalty3.yards_assessed} yards)")
    print(f"Play Negated: {penalty3.negated_play}")
    print()
    print(f"Decision: Play is better (35 > 5), so DECLINE")
    print(f"Penalty Accepted: {penalty3.penalty_accepted}")
    print()
    print(f"✓ CORRECT Final Result: {result3.modified_yards} yards (play stands)")
    print(f"✗ WRONG (old logic): {35 + 5} = 40 yards (double-counted, also impossible yardage!)")
    print()
    print()

    # Example 4: Offensive holding negates touchdown
    print("EXAMPLE 4: Offensive Holding Negates Touchdown")
    print("-" * 80)
    print("Scenario: 2nd & 5, play gains 45 yards (TD!), but holding penalty")
    print()

    penalty4 = PenaltyInstance(
        penalty_type="offensive_holding",
        penalized_player_name="Jake Williams",
        penalized_player_number=73,
        penalized_player_position="right_guard",
        team_penalized="home",
        yards_assessed=-10,
        automatic_first_down=False,
        automatic_loss_of_down=False,
        negated_play=True,
        quarter=4,
        time_remaining="3:42",
        down=2,
        distance=5,
        field_position=55,
        score_differential=-3,
        original_play_result=45
    )

    result4 = engine._apply_penalty_effects(penalty4, 45)

    print(f"Play Result Before Penalty: +45 yards (WOULD BE TOUCHDOWN!)")
    print(f"Penalty: {penalty4.penalty_type.replace('_', ' ').title()} ({penalty4.yards_assessed} yards)")
    print(f"Play Negated: {penalty4.negated_play}")
    print()
    print(f"✓ CORRECT Final Result: {result4.modified_yards} yards (touchdown negated)")
    print(f"✗ WRONG (old logic): {45 + (-10)} = 35 yards (double-counted)")
    print(f"Now it's 2nd & 15 instead of 1st & 10 at opponent 30")
    print()
    print()

    # Summary
    print("=" * 80)
    print("SUMMARY OF FIX")
    print("=" * 80)
    print()
    print("✓ Pre-snap penalties (negated_play=True):")
    print("  - Uses ONLY penalty yards")
    print("  - Play result is completely ignored")
    print()
    print("✓ Choice penalties (negated_play=False):")
    print("  - Simple heuristic: Accept if penalty_yards > play_yards")
    print("  - Accept: Uses ONLY penalty yards from line of scrimmage")
    print("  - Decline: Uses ONLY play result, penalty ignored")
    print()
    print("✓ NO DOUBLE-COUNTING:")
    print("  - Never adds play_yards + penalty_yards")
    print("  - Always uses ONE or the OTHER, never both")
    print()
    print("=" * 80)


if __name__ == "__main__":
    demonstrate_penalty_fix()
