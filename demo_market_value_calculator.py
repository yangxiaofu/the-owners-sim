"""
Market Value Calculator Demo

Quick demonstration of contract value calculations for NFL players.
Shows how AI will calculate offers for free agents and franchise tags.
"""

from offseason.market_value_calculator import MarketValueCalculator


def print_contract(player_name: str, contract: dict):
    """Pretty print contract details."""
    print(f"\n📋 {player_name}")
    print(f"   AAV:        ${contract['aav']:.2f}M")
    print(f"   Total:      ${contract['total_value']:.2f}M over {contract['years']} years")
    print(f"   Guaranteed: ${contract['guaranteed']:.2f}M ({contract['guarantee_percentage']:.1f}%)")
    print(f"   Signing:    ${contract['signing_bonus']:.2f}M")


def main():
    """Run market value calculator demo."""
    print("=" * 70)
    print("NFL Market Value Calculator Demo")
    print("=" * 70)

    calc = MarketValueCalculator()

    print("\n🏈 ELITE PLAYERS")
    print("-" * 70)

    # Elite QB (Patrick Mahomes clone)
    mahomes = calc.calculate_player_value(
        position='quarterback',
        overall=95,
        age=28,
        years_pro=7
    )
    print_contract("Patrick Mahomes (95 OVR QB, Age 28)", mahomes)

    # Elite WR (Tyreek Hill clone)
    hill = calc.calculate_player_value(
        position='wide_receiver',
        overall=93,
        age=29,
        years_pro=8
    )
    print_contract("Tyreek Hill (93 OVR WR, Age 29)", hill)

    # Elite Edge Rusher (Myles Garrett clone)
    garrett = calc.calculate_player_value(
        position='defensive_end',
        overall=94,
        age=28,
        years_pro=7
    )
    print_contract("Myles Garrett (94 OVR DE, Age 28)", garrett)

    print("\n\n💰 GOOD STARTERS")
    print("-" * 70)

    # Good OL (Orlando Brown clone)
    brown = calc.calculate_player_value(
        position='left_tackle',
        overall=85,
        age=27,
        years_pro=6
    )
    print_contract("Orlando Brown (85 OVR LT, Age 27)", brown)

    # Good CB (L'Jarius Sneed clone)
    sneed = calc.calculate_player_value(
        position='cornerback',
        overall=85,
        age=27,
        years_pro=5
    )
    print_contract("L'Jarius Sneed (85 OVR CB, Age 27)", sneed)

    print("\n\n⚠️  AGE DISCOUNTS")
    print("-" * 70)

    # Veteran RB (Derrick Henry clone)
    henry = calc.calculate_player_value(
        position='running_back',
        overall=88,
        age=30,
        years_pro=8
    )
    print_contract("Derrick Henry (88 OVR RB, Age 30)", henry)

    # Young promising QB
    young_qb = calc.calculate_player_value(
        position='quarterback',
        overall=85,
        age=24,
        years_pro=2
    )
    print_contract("Young QB (85 OVR, Age 24)", young_qb)

    print("\n\n🏷️  FRANCHISE TAG VALUES (2025)")
    print("-" * 70)

    positions = [
        ('quarterback', 'QB'),
        ('defensive_end', 'EDGE'),
        ('wide_receiver', 'WR'),
        ('left_tackle', 'OT'),
        ('cornerback', 'CB'),
        ('running_back', 'RB'),
    ]

    for position, abbrev in positions:
        tag_value = calc.calculate_franchise_tag_value(position)
        print(f"   {abbrev:8} ${tag_value:,}")

    print("\n\n📊 CONTRACT COMPARISON")
    print("-" * 70)
    print(f"   Elite QB:     ${mahomes['aav']:.1f}M AAV")
    print(f"   Elite Edge:   ${garrett['aav']:.1f}M AAV")
    print(f"   Good OT:      ${brown['aav']:.1f}M AAV")
    print(f"   Good CB:      ${sneed['aav']:.1f}M AAV")
    print(f"   Veteran RB:   ${henry['aav']:.1f}M AAV")

    print("\n" + "=" * 70)
    print("Demo Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
