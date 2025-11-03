"""
Real-World NFL Trade Benchmarking Script

Validates the Trade Value Calculator against 10 historical NFL trades.
Compares calculator verdicts with real-world assessments.

Target: 85%+ accuracy against real NFL trade evaluations

Usage:
    PYTHONPATH=src python demo/trade_value_demo/benchmark_trades.py

    Or run from anywhere:
    python demo/trade_value_demo/benchmark_trades.py
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple

# Add src to path for imports (works from any directory)
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from transactions.models import DraftPick, TradeAsset, AssetType, TradeProposal, FairnessRating
from transactions.trade_value_calculator import TradeValueCalculator


def load_historical_trades(file_path: Path = None) -> Dict:
    """Load historical NFL trades from JSON file"""
    if file_path is None:
        # Default to real_world_trades.json in same directory as this script
        file_path = Path(__file__).parent / "real_world_trades.json"

    with open(file_path, 'r') as f:
        return json.load(f)


def convert_json_to_trade_assets(assets_json: List[Dict], team_id: int, calc: TradeValueCalculator) -> List[TradeAsset]:
    """Convert JSON asset definitions to TradeAsset objects"""
    assets = []

    for asset_json in assets_json:
        if asset_json["type"] == "player":
            # Create player asset
            asset = TradeAsset(
                asset_type=AssetType.PLAYER,
                player_name=asset_json["name"],
                position=asset_json["position"],
                overall_rating=asset_json["overall_rating"],
                age=asset_json["age"],
                years_pro=asset_json.get("years_pro"),
                contract_years_remaining=asset_json.get("contract_years_remaining", 0),
                annual_cap_hit=asset_json.get("annual_cap_hit", 0)
            )

            # Calculate value
            asset.trade_value = calc.calculate_player_value(
                overall_rating=asset.overall_rating,
                position=asset.position,
                age=asset.age,
                contract_years_remaining=asset.contract_years_remaining,
                annual_cap_hit=asset.annual_cap_hit
            )

        elif asset_json["type"] == "draft_pick":
            # Create draft pick asset
            pick = DraftPick(
                round=asset_json["round"],
                year=asset_json["year"],
                original_team_id=team_id,
                current_team_id=team_id
            )
            pick.overall_pick_projected = asset_json["overall_pick_projected"]

            asset = TradeAsset(
                asset_type=AssetType.DRAFT_PICK,
                draft_pick=pick
            )

            # Calculate value
            asset.trade_value = calc.calculate_pick_value(pick)

        else:
            raise ValueError(f"Unknown asset type: {asset_json['type']}")

        assets.append(asset)

    return assets


def map_real_world_verdict_to_rating(verdict: str) -> List[FairnessRating]:
    """
    Map real-world trade verdicts to acceptable FairnessRating values.

    Returns list of ratings that would be considered matching the real-world verdict.
    """
    verdict_map = {
        "VERY_FAIR": [FairnessRating.VERY_FAIR],
        "FAIR": [FairnessRating.FAIR, FairnessRating.VERY_FAIR],  # VERY_FAIR also acceptable
        "SLIGHTLY_UNFAIR": [FairnessRating.SLIGHTLY_UNFAIR, FairnessRating.FAIR],  # Close to fair
        "VERY_UNFAIR": [FairnessRating.VERY_UNFAIR]
    }
    return verdict_map.get(verdict, [])


def evaluate_trade(trade_data: Dict, calc: TradeValueCalculator) -> Tuple[TradeProposal, bool, str]:
    """
    Evaluate a single historical trade.

    Returns:
        (TradeProposal, match: bool, explanation: str)
    """
    # Convert JSON assets to TradeAsset objects
    team1_assets = convert_json_to_trade_assets(trade_data["team1"]["assets"], 1, calc)
    team2_assets = convert_json_to_trade_assets(trade_data["team2"]["assets"], 2, calc)

    # Evaluate trade
    proposal = calc.evaluate_trade(
        team1_id=1,
        team1_assets=team1_assets,
        team2_id=2,
        team2_assets=team2_assets
    )

    # Compare with real-world verdict
    real_world_verdict = trade_data["real_world_verdict"]
    acceptable_ratings = map_real_world_verdict_to_rating(real_world_verdict)

    match = proposal.fairness_rating in acceptable_ratings

    # Generate explanation
    if match:
        explanation = f"✓ MATCH: Calculator rated {proposal.fairness_rating.value}, real world: {real_world_verdict}"
    else:
        explanation = f"✗ MISS: Calculator rated {proposal.fairness_rating.value}, real world: {real_world_verdict}"

    return proposal, match, explanation


def print_trade_detail(trade_data: Dict, proposal: TradeProposal, match: bool, explanation: str):
    """Print detailed trade evaluation"""
    print(f"\n{'=' * 80}")
    print(f"  {trade_data['name']} ({trade_data['year']})")
    print(f"{'=' * 80}")
    print(f"{trade_data['description']}\n")

    # Team 1
    print(f"--- {trade_data['team1']['name'].upper()} SENDS ---")
    for asset in proposal.team1_assets:
        print(f"  {asset} → {asset.trade_value:.1f} units")
    print(f"  TOTAL: {proposal.team1_total_value:.1f} units\n")

    # Team 2
    print(f"--- {trade_data['team2']['name'].upper()} SENDS ---")
    for asset in proposal.team2_assets:
        print(f"  {asset} → {asset.trade_value:.1f} units")
    print(f"  TOTAL: {proposal.team2_total_value:.1f} units\n")

    # Evaluation
    print(f"VALUE RATIO: {proposal.value_ratio:.3f}")
    print(f"CALCULATOR VERDICT: {proposal.fairness_rating.value}")
    print(f"REAL WORLD VERDICT: {trade_data['real_world_verdict']}\n")

    print(explanation)

    if not match:
        diff = proposal.get_value_difference()
        winner = proposal.get_winning_team()
        if winner:
            team_name = trade_data[f"team{winner}"]["name"]
            print(f"  Calculator: {team_name} wins by {diff:.1f} units")

    print(f"\nNOTES: {trade_data['notes']}")


def run_benchmark():
    """Run complete benchmarking against historical trades"""
    print("\n" + "🏈" * 40)
    print("\n  NFL TRADE VALUE CALCULATOR - REAL-WORLD BENCHMARK")
    print("  Validating Against 10 Historical NFL Trades")
    print("\n" + "🏈" * 40)

    # Load trades
    trades_data = load_historical_trades()
    trades = trades_data["trades"]

    print(f"\n📊 Loaded {len(trades)} historical NFL trades\n")

    # Initialize calculator
    calc = TradeValueCalculator(current_year=2025)

    # Track results
    results = []
    matches = 0
    total = len(trades)

    # Evaluate each trade
    for i, trade_data in enumerate(trades, 1):
        print(f"\n{'─' * 80}")
        print(f"TRADE {i}/{total}")

        proposal, match, explanation = evaluate_trade(trade_data, calc)

        if match:
            matches += 1

        results.append({
            "name": trade_data["name"],
            "match": match,
            "calculator_verdict": proposal.fairness_rating.value,
            "real_world_verdict": trade_data["real_world_verdict"],
            "value_ratio": proposal.value_ratio
        })

        # Print detailed evaluation
        print_trade_detail(trade_data, proposal, match, explanation)

    # Print summary
    print("\n\n" + "=" * 80)
    print("  BENCHMARK SUMMARY")
    print("=" * 80)

    accuracy = (matches / total) * 100
    print(f"\nACCURACY: {matches}/{total} ({accuracy:.1f}%)")
    print(f"TARGET: 85%+ accuracy\n")

    if accuracy >= 85:
        print("✅ TARGET MET! Calculator demonstrates strong real-world alignment.")
    elif accuracy >= 70:
        print("⚠️  CLOSE TO TARGET. Calculator shows good but not excellent alignment.")
    else:
        print("❌ BELOW TARGET. Calculator needs calibration adjustments.")

    # Detailed breakdown
    print("\nDETAILED BREAKDOWN:")
    print(f"{'Trade':<40} {'Calculator':<20} {'Real World':<20} {'Match':<10}")
    print("-" * 90)

    for result in results:
        match_symbol = "✓" if result["match"] else "✗"
        print(f"{result['name']:<40} {result['calculator_verdict']:<20} {result['real_world_verdict']:<20} {match_symbol:<10}")

    # Analysis
    print("\n\nANALYSIS:")

    # Count verdict distributions
    calc_verdicts = {}
    real_verdicts = {}
    for result in results:
        calc_v = result["calculator_verdict"]
        real_v = result["real_world_verdict"]
        calc_verdicts[calc_v] = calc_verdicts.get(calc_v, 0) + 1
        real_verdicts[real_v] = real_verdicts.get(real_v, 0) + 1

    print("\nCalculator Verdict Distribution:")
    for verdict, count in sorted(calc_verdicts.items()):
        print(f"  {verdict}: {count} trades ({count/total*100:.1f}%)")

    print("\nReal World Verdict Distribution:")
    for verdict, count in sorted(real_verdicts.items()):
        print(f"  {verdict}: {count} trades ({count/total*100:.1f}%)")

    # Identify patterns in mismatches
    mismatches = [r for r in results if not r["match"]]
    if mismatches:
        print(f"\nMISMATCH ANALYSIS ({len(mismatches)} trades):")
        for result in mismatches:
            print(f"  {result['name']}:")
            print(f"    Calculator: {result['calculator_verdict']} (ratio: {result['value_ratio']:.3f})")
            print(f"    Real World: {result['real_world_verdict']}")

    # Recommendations
    print("\n\nRECOMMENDATIONS:")
    if accuracy >= 85:
        print("  ✓ Calculator is well-calibrated for production use")
        print("  ✓ Ready for Phase 1.3 (GM archetype integration)")
    else:
        print("  • Review mismatches to identify systematic biases")
        print("  • Consider adjusting position multipliers or age curves")
        print("  • Test with additional historical trades")
        print("  • Validate against specific position groups (QB, WR, Edge)")


if __name__ == "__main__":
    run_benchmark()
