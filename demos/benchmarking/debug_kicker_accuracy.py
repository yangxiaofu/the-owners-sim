"""
Debug script to trace exact kicker accuracy calculation.
"""

import os
import sys
import random

# Add paths
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from team_management.personnel import TeamRosterGenerator


def debug_kicker_ratings():
    """Check what ratings synthetic kickers actually have."""
    print("=" * 80)
    print("SYNTHETIC KICKER RATINGS DEBUG")
    print("=" * 80)

    # Create a synthetic roster
    roster = TeamRosterGenerator.generate_synthetic_roster(team_id=1)

    # Find the kicker
    from team_management.players.player import Position
    kickers = [p for p in roster if p.primary_position == Position.K]

    if not kickers:
        print("No kicker found!")
        return

    kicker = kickers[0]
    print(f"\nKicker: {kicker.name}")
    print(f"Position: {kicker.primary_position}")
    print(f"\nAll ratings:")
    for key, value in kicker.ratings.items():
        print(f"  {key}: {value}")

    print(f"\nget_rating('accuracy'): {kicker.get_rating('accuracy')}")
    print(f"get_rating('overall'): {kicker.get_rating('overall')}")
    print(f"get_rating('kicking_power'): {kicker.get_rating('kicking_power')}")

    # Simulate the modifier calculation
    print("\n" + "=" * 80)
    print("SIMULATING _get_kicker_modifier() LOGIC")
    print("=" * 80)

    kicker_accuracy = 75  # Default
    if hasattr(kicker, 'get_rating'):
        kicker_accuracy = kicker.get_rating('accuracy')
        print(f"1. get_rating('accuracy') = {kicker_accuracy}")

        # If accuracy not defined (returns default 50), use overall instead
        if kicker_accuracy <= 50:
            kicker_accuracy = kicker.get_rating('overall')
            print(f"2. Accuracy <= 50, using get_rating('overall') = {kicker_accuracy}")

            # Still default? Use 75 as reasonable average
            if kicker_accuracy <= 50:
                kicker_accuracy = 75
                print(f"3. Overall also <= 50, using default 75")

    print(f"\nFinal kicker_accuracy for modifier calculation: {kicker_accuracy}")

    # Calculate modifier
    if kicker_accuracy >= 90:
        modifier = 1.05
        tier = "Elite"
    elif kicker_accuracy >= 80:
        modifier = 1.02
        tier = "Good"
    elif kicker_accuracy >= 70:
        modifier = 1.0
        tier = "Average"
    elif kicker_accuracy >= 60:
        modifier = 0.97
        tier = "Below Average"
    else:
        modifier = 0.94
        tier = "Poor"

    print(f"Kicker tier: {tier}")
    print(f"Kicker modifier: {modifier}")

    # Now simulate XP success rates with this modifier
    print("\n" + "=" * 80)
    print("SIMULATING 1000 EXTRA POINT ATTEMPTS")
    print("=" * 80)

    base_success_rate = 0.94

    # Simulate without snap/hold/block issues
    made = 0
    attempts = 1000
    for _ in range(attempts):
        # From _simulate_pat_execution
        kicker_penalty = 1.0 - modifier  # modifier=1.0 for avg kicker -> penalty=0
        env_penalty = 0  # Clear weather

        total_penalty = kicker_penalty + env_penalty
        final_success_rate = base_success_rate - total_penalty

        # Clamp
        final_success_rate = max(0.85, min(0.98, final_success_rate))

        if random.random() < final_success_rate:
            made += 1

    print(f"Base success rate: {base_success_rate:.1%}")
    print(f"Kicker penalty: {1.0 - modifier:.3f}")
    print(f"Final success rate (clamped): {final_success_rate:.1%}")
    print(f"\nSimulation: {made}/{attempts} = {made/attempts:.1%}")

    # Now simulate WITH snap/hold/block
    print("\n" + "=" * 80)
    print("SIMULATING WITH SNAP/HOLD/BLOCK FACTORS (actual game flow)")
    print("=" * 80)

    made = 0
    blocked = 0
    snap_hold_miss = 0
    kick_miss = 0

    for _ in range(attempts):
        # Phase 1: Snap/hold quality (from _evaluate_snap_quality)
        # Synthetic long snapper has awareness ~75, so quality = 0.95
        snap_quality = 0.95
        hold_quality = min(0.99, snap_quality * 1.02)  # ~0.969

        # Check for catastrophic snap/hold failure
        if snap_quality < 0.80 or hold_quality < 0.80:
            if random.random() < 0.10:
                snap_hold_miss += 1
                continue

        # Phase 2: Block check (~1.5%)
        if random.random() < 0.015:
            blocked += 1
            continue

        # Phase 3: Kick execution
        kicker_penalty = 1.0 - modifier
        env_penalty = 0
        total_penalty = kicker_penalty + env_penalty
        final_success_rate = base_success_rate - total_penalty
        final_success_rate = max(0.85, min(0.98, final_success_rate))

        if random.random() < final_success_rate:
            made += 1
        else:
            kick_miss += 1

    print(f"Made: {made}")
    print(f"Blocked: {blocked}")
    print(f"Snap/Hold Miss: {snap_hold_miss}")
    print(f"Kick Miss: {kick_miss}")
    print(f"Total: {made + blocked + snap_hold_miss + kick_miss}")
    print(f"\nActual success rate: {made/attempts:.1%}")


if __name__ == "__main__":
    debug_kicker_ratings()