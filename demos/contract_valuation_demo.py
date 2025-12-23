"""
Contract Valuation Engine Demo

Run with: python demos/contract_valuation_demo.py

Demonstrates:
- Mock players with realistic stats through the valuation engine
- Full valuation breakdown with factor contributions
- Side-by-side comparison with real NFL contracts
- GM style variance (same player, different GMs)
- Pressure scenario impact (secure vs hot seat)
"""

import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

import json
from typing import Dict, Any, List, Optional

from contract_valuation.engine import ContractValuationEngine
from contract_valuation.models import ValuationResult, FactorWeights
from contract_valuation.context import (
    ValuationContext,
    OwnerContext,
    JobSecurityContext,
)
from contract_valuation.testing.benchmark_cases import (
    ELITE_CASES,
    STARTER_CASES,
    AGE_EXTREME_CASES,
    GM_VARIANCE_CASES,
    PRESSURE_CASES,
    BenchmarkCase,
)
from team_management.gm_archetype import GMArchetype


# Box drawing characters for clean output
BOX_TL = "┌"
BOX_TR = "┐"
BOX_BL = "└"
BOX_BR = "┘"
BOX_H = "─"
BOX_V = "│"
BOX_ML = "├"
BOX_MR = "┤"


def load_nfl_contracts() -> List[Dict[str, Any]]:
    """Load real NFL contract data."""
    contracts_path = Path(__file__).parent.parent / "src" / "contract_valuation" / "benchmarks" / "nfl_contracts.json"
    with open(contracts_path) as f:
        data = json.load(f)
    return data["contracts"]


def get_comparables(contracts: List[Dict], position: str, tier: str = "elite") -> List[Dict]:
    """Get comparable contracts by position and tier."""
    # Map generic positions to specific
    position_map = {
        "S": ["S", "FS", "SS"],
        "LB": ["LB", "MLB", "LOLB", "ROLB"],
        "OG": ["LG", "RG", "G"],
        "OT": ["LT", "RT", "T"],
    }

    positions_to_match = position_map.get(position, [position])

    matching = [
        c for c in contracts
        if c["position"] in positions_to_match and c.get("tier") == tier
    ]

    # If no tier match, get all at position
    if not matching:
        matching = [c for c in contracts if c["position"] in positions_to_match]

    return matching[:4]  # Max 4 comparables


def format_money(amount: int) -> str:
    """Format dollar amount with commas."""
    return f"${amount:,}"


def format_money_short(amount: int) -> str:
    """Format dollar amount in millions (e.g., $45.0M)."""
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    return f"${amount / 1_000:.0f}K"


def print_header(title: str):
    """Print a section header."""
    print()
    print("=" * 80)
    print(f"  {title}")
    print("=" * 80)
    print()


def print_subheader(title: str):
    """Print a subsection header."""
    print()
    print("-" * 80)
    print(f"  {title}")
    print("-" * 80)


def print_player_info(case: BenchmarkCase):
    """Print player information."""
    player = case.player_data
    stats = player.get("stats", {})

    print(f"PLAYER: {case.name}")
    print(f"Position: {player['position']} | Age: {player['age']} | Overall: {player['overall_rating']}")

    # Format stats based on position
    if stats:
        stat_strs = []
        if "pass_yards" in stats:
            stat_strs.append(f"{stats['pass_yards']:,} pass yds")
        if "pass_tds" in stats:
            stat_strs.append(f"{stats['pass_tds']} TDs")
        if "passer_rating" in stats:
            stat_strs.append(f"{stats['passer_rating']:.1f} rating")
        if "rush_yards" in stats:
            stat_strs.append(f"{stats['rush_yards']:,} rush yds")
        if "rush_tds" in stats:
            stat_strs.append(f"{stats['rush_tds']} TDs")
        if "rec_yards" in stats:
            stat_strs.append(f"{stats['rec_yards']:,} rec yds")
        if "receptions" in stats:
            stat_strs.append(f"{stats['receptions']} rec")
        if "rec_tds" in stats:
            stat_strs.append(f"{stats['rec_tds']} TDs")
        if "sacks" in stats:
            stat_strs.append(f"{stats['sacks']:.1f} sacks")
        if "interceptions" in stats:
            stat_strs.append(f"{stats['interceptions']} INTs")
        if "tackles" in stats:
            stat_strs.append(f"{stats['tackles']} tackles")

        if stat_strs:
            print(f"Stats: {', '.join(stat_strs)}")
    print()


def print_valuation_box(result: ValuationResult):
    """Print valuation result in a formatted box."""
    offer = result.offer
    width = 77

    print(f"{BOX_TL}{BOX_H * width}{BOX_TR}")
    print(f"{BOX_V} {'ENGINE VALUATION':<{width-1}}{BOX_V}")
    print(f"{BOX_ML}{BOX_H * width}{BOX_MR}")

    # Contract details
    print(f"{BOX_V}  AAV:         {format_money(offer.aav):<{width-16}}{BOX_V}")
    print(f"{BOX_V}  Years:       {offer.years:<{width-16}}{BOX_V}")
    print(f"{BOX_V}  Total:       {format_money(offer.total_value):<{width-16}}{BOX_V}")
    print(f"{BOX_V}  Guaranteed:  {format_money(offer.guaranteed)} ({offer.guaranteed_pct:.0%}){' ' * (width-35)}{BOX_V}")
    print(f"{BOX_V}{' ' * width}{BOX_V}")

    # Factor breakdown
    print(f"{BOX_V}  {'Factor Breakdown:':<{width-3}}{BOX_V}")

    weights = result.weights_used
    for factor_result in result.raw_factor_results:
        name = factor_result.name
        raw_value = factor_result.raw_value

        # Get weight for this factor
        if "stats" in name.lower():
            weight = weights.stats_weight
        elif "scouting" in name.lower():
            weight = weights.scouting_weight
        elif "market" in name.lower():
            weight = weights.market_weight
        elif "rating" in name.lower():
            weight = weights.rating_weight
        else:
            weight = 0.25

        weight_pct = f"(weight: {weight:.0%})"
        factor_line = f"    {name.replace('_', ' ').title()}: {format_money_short(raw_value)} {weight_pct}"
        print(f"{BOX_V}  {factor_line:<{width-3}}{BOX_V}")

    print(f"{BOX_V}{' ' * width}{BOX_V}")

    # GM style and pressure
    print(f"{BOX_V}  GM Style: {result.gm_style_description:<{width-13}}{BOX_V}")

    if result.pressure_adjustment_pct != 0:
        adj = f"+{result.pressure_adjustment_pct:.0%}" if result.pressure_adjustment_pct > 0 else f"{result.pressure_adjustment_pct:.0%}"
        pressure_str = f"Pressure: {result.pressure_description} ({adj} adjustment)"
    else:
        pressure_str = f"Pressure: {result.pressure_description}"
    print(f"{BOX_V}  {pressure_str:<{width-3}}{BOX_V}")

    print(f"{BOX_BL}{BOX_H * width}{BOX_BR}")


def print_comparables_box(comparables: List[Dict], engine_aav: int):
    """Print NFL comparables in a formatted box."""
    if not comparables:
        print("  (No NFL comparables found for this position)")
        return

    width = 77

    print(f"{BOX_TL}{BOX_H * width}{BOX_TR}")
    print(f"{BOX_V} {'REAL NFL COMPARABLES':<{width-1}}{BOX_V}")
    print(f"{BOX_ML}{BOX_H * width}{BOX_MR}")

    for c in comparables:
        name = c["player_name"]
        team = c["team"].split()[-1][:3].upper()  # Get team abbreviation
        year = c["season_signed"]
        aav = format_money_short(c["aav"])
        years = c["years"]
        gtd_pct = c["guaranteed_pct"]

        line = f"{name} ({team}, {year})"
        details = f"{aav} AAV | {years} yrs | {gtd_pct:.0%} gtd"
        print(f"{BOX_V}  {line:<32}{details:<{width-35}}{BOX_V}")

    # Calculate average and deviation
    avg_aav = sum(c["aav"] for c in comparables) // len(comparables)
    deviation = (engine_aav - avg_aav) / avg_aav * 100

    print(f"{BOX_ML}{BOX_H * width}{BOX_MR}")

    avg_line = f"Average: {format_money_short(avg_aav)} AAV"

    if abs(deviation) <= 15:
        status = "within range"
    elif deviation > 0:
        status = "above market"
    else:
        status = "below market"

    dev_line = f"Engine Deviation: {deviation:+.1f}% ({status})"

    print(f"{BOX_V}  {avg_line:<{width-3}}{BOX_V}")
    print(f"{BOX_V}  {dev_line:<{width-3}}{BOX_V}")

    print(f"{BOX_BL}{BOX_H * width}{BOX_BR}")


def run_single_valuation(
    engine: ContractValuationEngine,
    case: BenchmarkCase,
    context: ValuationContext,
    owner_context: OwnerContext,
    gm_archetype: Optional[GMArchetype] = None,
) -> ValuationResult:
    """Run a single valuation."""
    return engine.valuate(
        player_data=case.player_data,
        valuation_context=context,
        owner_context=owner_context,
        gm_archetype=gm_archetype,
    )


def demo_elite_players(engine: ContractValuationEngine, nfl_contracts: List[Dict]):
    """Demo elite player valuations with NFL comparisons."""
    print_header("SECTION 1: ELITE PLAYER SHOWCASE")
    print("Comparing engine valuations to real NFL elite contracts")

    context = ValuationContext.create_default_2025()
    owner_context = OwnerContext.create_default("demo", 1)

    for case in ELITE_CASES:
        print_player_info(case)

        result = run_single_valuation(engine, case, context, owner_context)
        print_valuation_box(result)

        print()
        comparables = get_comparables(nfl_contracts, case.player_data["position"], "elite")
        print_comparables_box(comparables, result.offer.aav)

        print()
        print(f"  Expected Range: {format_money(case.expected_aav_min)} - {format_money(case.expected_aav_max)}")
        in_range = case.expected_aav_min <= result.offer.aav <= case.expected_aav_max
        print(f"  Status: {'PASS' if in_range else 'DEVIATION'}")
        print()
        print("-" * 80)


def demo_starter_vs_backup(engine: ContractValuationEngine):
    """Demo how rating affects valuation."""
    print_header("SECTION 2: TIER COMPARISON (Starter vs Backup)")
    print("Same positions at different rating tiers")

    context = ValuationContext.create_default_2025()
    owner_context = OwnerContext.create_default("demo", 1)

    # Pick WR starter and backup
    from contract_valuation.testing.benchmark_cases import BACKUP_CASES

    starter_wr = next((c for c in STARTER_CASES if c.player_data["position"] == "WR"), None)
    backup_wr = next((c for c in BACKUP_CASES if c.player_data["position"] == "WR"), None)

    if starter_wr and backup_wr:
        print_subheader("Wide Receiver Comparison")

        for label, case in [("STARTER", starter_wr), ("BACKUP", backup_wr)]:
            print(f"\n  [{label}]")
            print_player_info(case)
            result = run_single_valuation(engine, case, context, owner_context)

            print(f"  AAV: {format_money(result.offer.aav)}")
            print(f"  Years: {result.offer.years}")
            print(f"  Guaranteed: {result.offer.guaranteed_pct:.0%}")

        print()


def demo_age_impact(engine: ContractValuationEngine):
    """Demo how age affects contract structure."""
    print_header("SECTION 3: AGE IMPACT DEMO")
    print("How age affects AAV and contract length")

    context = ValuationContext.create_default_2025()
    owner_context = OwnerContext.create_default("demo", 1)

    for case in AGE_EXTREME_CASES[:4]:  # First 4 age cases
        print_player_info(case)
        result = run_single_valuation(engine, case, context, owner_context)

        print(f"  AAV: {format_money(result.offer.aav)}")
        print(f"  Years: {result.offer.years}")
        print(f"  Guaranteed: {format_money(result.offer.guaranteed)} ({result.offer.guaranteed_pct:.0%})")
        print(f"  Notes: {case.notes}")
        print()


def demo_gm_variance(engine: ContractValuationEngine):
    """Demo how GM style affects valuation."""
    print_header("SECTION 4: GM STYLE VARIANCE")
    print("Same player valued by different GM personalities")

    context = ValuationContext.create_default_2025()

    # Use the variance test player
    from contract_valuation.testing.benchmark_cases import _VARIANCE_TEST_PLAYER

    player = _VARIANCE_TEST_PLAYER
    print(f"Player: Quality WR | Age: {player['age']} | Overall: {player['overall_rating']}")
    print()

    gm_styles = [
        ("Analytics-Heavy", GMArchetype(
            name="Analytics GM",
            description="Stats-driven decision maker",
            analytics_preference=0.90,
            scouting_preference=0.30,
            market_awareness=0.50,
        )),
        ("Scout-Focused", GMArchetype(
            name="Scout GM",
            description="Eye-test evaluator",
            analytics_preference=0.30,
            scouting_preference=0.90,
            market_awareness=0.50,
        )),
        ("Market-Driven", GMArchetype(
            name="Market GM",
            description="Follows market rates",
            analytics_preference=0.30,
            scouting_preference=0.30,
            market_awareness=0.90,
        )),
        ("Balanced", GMArchetype(
            name="Balanced GM",
            description="Uses all inputs equally",
            analytics_preference=0.50,
            scouting_preference=0.50,
            market_awareness=0.50,
        )),
    ]

    results = []
    owner_context = OwnerContext.create_default("demo", 1)

    for style_name, gm in gm_styles:
        result = engine.valuate(
            player_data=player,
            valuation_context=context,
            owner_context=owner_context,
            gm_archetype=gm,
        )
        results.append((style_name, result))

    # Print comparison table
    print(f"  {'GM Style':<20} {'AAV':<15} {'Years':<8} {'Gtd %':<10}")
    print(f"  {'-'*20} {'-'*15} {'-'*8} {'-'*10}")

    aavs = []
    for style_name, result in results:
        aav = format_money_short(result.offer.aav)
        years = result.offer.years
        gtd = f"{result.offer.guaranteed_pct:.0%}"
        print(f"  {style_name:<20} {aav:<15} {years:<8} {gtd:<10}")
        aavs.append(result.offer.aav)

    # Calculate variance
    min_aav = min(aavs)
    max_aav = max(aavs)
    variance_pct = (max_aav - min_aav) / min_aav * 100

    print()
    print(f"  Variance: {format_money_short(max_aav - min_aav)} ({variance_pct:.1f}%)")
    print(f"  Range: {format_money_short(min_aav)} - {format_money_short(max_aav)}")


def demo_pressure_scenarios(engine: ContractValuationEngine):
    """Demo how GM job security affects offers."""
    print_header("SECTION 5: PRESSURE SCENARIOS")
    print("How GM job security affects contract aggressiveness")

    context = ValuationContext.create_default_2025()

    # Use the pressure test player
    from contract_valuation.testing.benchmark_cases import _PRESSURE_TEST_PLAYER

    player = _PRESSURE_TEST_PLAYER
    print(f"Player: Quality EDGE | Age: {player['age']} | Overall: {player['overall_rating']}")
    print(f"Stats: {player['stats'].get('sacks', 0):.1f} sacks")
    print()

    pressure_scenarios = [
        ("Secure (5yr tenure, playoff success)", JobSecurityContext.create_secure()),
        ("Normal (3yr tenure, .500 record)", JobSecurityContext(
            tenure_years=3,
            playoff_appearances=1,
            recent_win_pct=0.50,
            owner_patience=0.50,
        )),
        ("Hot Seat (1yr tenure, losing record)", JobSecurityContext.create_hot_seat()),
    ]

    results = []
    for scenario_name, job_security in pressure_scenarios:
        security_score = job_security.calculate_security_score()
        owner_context = OwnerContext(
            dynasty_id="demo",
            team_id=1,
            job_security=job_security,
            owner_philosophy="balanced",
            team_philosophy="maintain",
            win_now_mode=security_score > 0.6,
            max_contract_years=5,
            max_guaranteed_pct=0.65,
        )

        result = engine.valuate(
            player_data=player,
            valuation_context=context,
            owner_context=owner_context,
        )
        results.append((scenario_name, result, owner_context))

    # Print comparison
    print(f"  {'Scenario':<45} {'AAV':<12} {'Pressure Adj':<15}")
    print(f"  {'-'*45} {'-'*12} {'-'*15}")

    for scenario_name, result, _ in results:
        aav = format_money_short(result.offer.aav)
        adj = result.pressure_adjustment_pct
        adj_str = f"{adj:+.0%}" if adj != 0 else "0%"
        print(f"  {scenario_name:<45} {aav:<12} {adj_str:<15}")

    # Calculate overpay difference
    base_aav = results[0][1].offer.aav  # Secure GM
    hot_seat_aav = results[-1][1].offer.aav  # Hot seat GM
    overpay = hot_seat_aav - base_aav
    overpay_pct = overpay / base_aav * 100

    print()
    print(f"  Hot Seat Overpay: {format_money_short(overpay)} ({overpay_pct:.1f}% more than secure GM)")


def print_summary(engine: ContractValuationEngine, nfl_contracts: List[Dict]):
    """Print a summary comparing all elite players to NFL data."""
    print_header("SUMMARY: ENGINE ACCURACY")

    context = ValuationContext.create_default_2025()
    owner_context = OwnerContext.create_default("demo", 1)

    total_deviation = 0
    count = 0

    print(f"  {'Player Type':<35} {'Engine AAV':<15} {'NFL Avg':<15} {'Deviation':<12}")
    print(f"  {'-'*35} {'-'*15} {'-'*15} {'-'*12}")

    for case in ELITE_CASES:
        result = run_single_valuation(engine, case, context, owner_context)
        comparables = get_comparables(nfl_contracts, case.player_data["position"], "elite")

        if comparables:
            avg_nfl = sum(c["aav"] for c in comparables) // len(comparables)
            deviation = (result.offer.aav - avg_nfl) / avg_nfl * 100
            total_deviation += abs(deviation)
            count += 1

            engine_str = format_money_short(result.offer.aav)
            nfl_str = format_money_short(avg_nfl)
            dev_str = f"{deviation:+.1f}%"

            print(f"  {case.name:<35} {engine_str:<15} {nfl_str:<15} {dev_str:<12}")

    avg_deviation = total_deviation / count if count > 0 else 0
    print()
    print(f"  Average Absolute Deviation: {avg_deviation:.1f}%")
    print(f"  Target: < 15%")
    print(f"  Status: {'PASS' if avg_deviation < 15 else 'NEEDS TUNING'}")


def main():
    """Run the full demo."""
    print()
    print("=" * 80)
    print("                    CONTRACT VALUATION ENGINE DEMO")
    print("=" * 80)
    print()
    print("This demo shows how the Contract Valuation Engine generates")
    print("realistic contract offers and compares them to actual NFL contracts.")
    print()

    # Initialize
    engine = ContractValuationEngine()
    nfl_contracts = load_nfl_contracts()

    print(f"Loaded {len(nfl_contracts)} real NFL contracts for comparison")
    print()

    # Run demo sections
    demo_elite_players(engine, nfl_contracts)
    demo_starter_vs_backup(engine)
    demo_age_impact(engine)
    demo_gm_variance(engine)
    demo_pressure_scenarios(engine)
    print_summary(engine, nfl_contracts)

    print()
    print("=" * 80)
    print("                           DEMO COMPLETE")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()
