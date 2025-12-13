#!/usr/bin/env python3
"""
Test script to verify QB scramble frequency after the fix.

This simulates the scramble decision logic to verify:
- Elite mobile QBs (mobility 90+) get ~15-20% scramble rate
- Average QBs (mobility 70) get ~5-8% scramble rate
- Pocket passers (mobility 50) get ~2-3% scramble rate
"""

import random


def calculate_scramble_chance(mobility: int, composure: int = 75) -> float:
    """Replicate the _calculate_scramble_chance() logic."""
    base_chance = 0.15  # 15% base

    if mobility >= 90:
        base_chance += 0.25  # 40% total
    elif mobility >= 85:
        base_chance += 0.18  # 33% total
    elif mobility >= 80:
        base_chance += 0.12  # 27% total
    elif mobility >= 75:
        base_chance += 0.05  # 20% total
    elif mobility < 65:
        base_chance -= 0.08  # 7% total

    if composure >= 85:
        base_chance += 0.05

    return min(0.50, max(0.05, base_chance))


def simulate_scrambles(mobility: int, composure: int = 75, num_plays: int = 1000) -> dict:
    """
    Simulate scramble decisions for a QB with given attributes.

    Returns dict with scramble statistics.
    """
    pressure_rate = 0.30  # ~30% of plays QB is pressured
    sack_rate = 0.09  # ~9% sack rate

    scramble_count = 0
    pressure_scrambles = 0
    sack_escape_scrambles = 0
    designed_scrambles = 0
    sacks = 0
    pressured_throws = 0
    clean_pockets = 0

    scramble_chance = calculate_scramble_chance(mobility, composure)

    for _ in range(num_plays):
        sack_roll = random.random()
        pressure_roll = random.random()

        would_be_sacked = sack_roll < sack_rate
        is_pressured = pressure_roll < pressure_rate

        scrambled = False

        # Check pressure/sack scramble
        if is_pressured or would_be_sacked:
            chance = scramble_chance
            if would_be_sacked:
                chance = min(0.70, chance * 1.5)

            if random.random() < chance:
                scrambled = True
                scramble_count += 1
                if would_be_sacked:
                    sack_escape_scrambles += 1
                else:
                    pressure_scrambles += 1
                would_be_sacked = False

        # Check designed scramble (clean pocket)
        if not scrambled and not would_be_sacked and not is_pressured:
            if mobility >= 85:
                designed_chance = (mobility - 80) / 200
                if random.random() < designed_chance:
                    scrambled = True
                    scramble_count += 1
                    designed_scrambles += 1

        if would_be_sacked:
            sacks += 1
        elif is_pressured and not scrambled:
            pressured_throws += 1
        elif not scrambled:
            clean_pockets += 1

    return {
        'mobility': mobility,
        'total_plays': num_plays,
        'scrambles': scramble_count,
        'scramble_pct': scramble_count / num_plays * 100,
        'pressure_scrambles': pressure_scrambles,
        'sack_escape_scrambles': sack_escape_scrambles,
        'designed_scrambles': designed_scrambles,
        'sacks': sacks,
        'sack_pct': sacks / num_plays * 100,
        'pressured_throws': pressured_throws,
        'clean_pockets': clean_pockets,
    }


def main():
    print("=" * 70)
    print("QB SCRAMBLE FREQUENCY TEST (After Fix)")
    print("=" * 70)
    print()

    # Test different QB types
    qb_types = [
        ("Lamar Jackson (Elite Mobile)", 92, 80),
        ("Josh Allen (Very Mobile)", 87, 82),
        ("Kyler Murray (Mobile)", 85, 75),
        ("Average QB", 70, 75),
        ("Tom Brady (Pocket Passer)", 50, 90),
    ]

    num_simulations = 10000  # ~300 games worth of pass plays

    for name, mobility, composure in qb_types:
        results = simulate_scrambles(mobility, composure, num_simulations)

        print(f"\n{name} (Mobility: {mobility}, Composure: {composure})")
        print("-" * 50)
        print(f"  Base scramble chance: {calculate_scramble_chance(mobility, composure):.1%}")
        print(f"  Total scrambles: {results['scrambles']} ({results['scramble_pct']:.1f}%)")
        print(f"    - Pressure scrambles: {results['pressure_scrambles']}")
        print(f"    - Sack escapes: {results['sack_escape_scrambles']}")
        print(f"    - Designed scrambles: {results['designed_scrambles']}")
        print(f"  Sacks taken: {results['sacks']} ({results['sack_pct']:.1f}%)")

        # Per-game estimate (35 pass attempts)
        per_game_scrambles = results['scramble_pct'] / 100 * 35
        print(f"  Estimated scrambles per game (35 attempts): {per_game_scrambles:.1f}")

    print("\n" + "=" * 70)
    print("EXPECTED VS ACTUAL COMPARISON")
    print("=" * 70)

    # Lamar Jackson expectations
    lamar_results = simulate_scrambles(92, 80, num_simulations)
    print(f"\nLamar Jackson:")
    print(f"  Expected: 5-7 scrambles per game")
    print(f"  Simulated: {lamar_results['scramble_pct'] / 100 * 35:.1f} scrambles per game")

    # Tom Brady expectations
    brady_results = simulate_scrambles(50, 90, num_simulations)
    print(f"\nTom Brady:")
    print(f"  Expected: 1-2 scrambles per game")
    print(f"  Simulated: {brady_results['scramble_pct'] / 100 * 35:.1f} scrambles per game")

    print("\n" + "=" * 70)
    print("SUCCESS!" if lamar_results['scramble_pct'] > 10 else "NEEDS TUNING")
    print("=" * 70)


if __name__ == "__main__":
    main()
