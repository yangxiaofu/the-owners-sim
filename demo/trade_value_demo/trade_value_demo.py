"""
Trade Value Calculator Interactive Demo

Demonstrates 5 realistic NFL trade scenarios plus interactive calculator mode.
Shows how the TradeValueCalculator evaluates players, draft picks, and complete trade packages.

Usage:
    PYTHONPATH=src python demo/trade_value_demo/trade_value_demo.py

    Or run from anywhere:
    python demo/trade_value_demo/trade_value_demo.py
"""

import sys
from pathlib import Path
from typing import List, Optional

# Add src to path for imports (works from any directory)
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from transactions.models import DraftPick, TradeAsset, AssetType, TradeProposal
from transactions.trade_value_calculator import TradeValueCalculator


def print_header(title: str):
    """Print formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_asset_details(asset: TradeAsset, calculator: TradeValueCalculator):
    """Print detailed asset information"""
    if asset.asset_type == AssetType.PLAYER:
        print(f"  {asset}")
        print(f"    Trade Value: {asset.trade_value:.1f} units")

        # Show calculation breakdown
        if asset.overall_rating and asset.position and asset.age:
            base_value = calculator.calculate_player_value(
                overall_rating=asset.overall_rating,
                position=asset.position,
                age=asset.age,
                contract_years_remaining=0,
                annual_cap_hit=0
            )
            print(f"    Base Value (no contract): {base_value:.1f} units")

            if asset.contract_years_remaining and asset.annual_cap_hit:
                cap_hit_millions = asset.annual_cap_hit / 1_000_000
                print(f"    Contract: {asset.contract_years_remaining}yr @ ${cap_hit_millions:.1f}M/yr")
    else:
        print(f"  {asset}")
        print(f"    Trade Value: {asset.trade_value:.1f} units")

        if asset.draft_pick:
            pick = asset.draft_pick
            if pick.overall_pick_projected:
                # Show what this pick is worth
                base_chart_value = calculator.draft_pick_values.get(pick.overall_pick_projected, 0)
                print(f"    Jimmy Johnson Chart: {base_chart_value:.1f} units")

                if pick.year > calculator.current_year:
                    years_out = pick.year - calculator.current_year
                    discount = (0.95 ** years_out)
                    print(f"    Future Discount: {discount:.2%} ({years_out} year{'s' if years_out > 1 else ''} out)")


def print_trade_summary(proposal: TradeProposal):
    """Print formatted trade summary"""
    print(f"\n{proposal.get_summary()}")

    # Add visual representation
    diff = proposal.get_value_difference()
    if diff > 0:
        winner = proposal.get_winning_team()
        if winner:
            print(f"\nValue Difference: {diff:.1f} units in favor of Team {winner}")


def scenario_1_elite_qb_trade():
    """
    Scenario 1: Elite QB for Multiple First Round Picks

    Based on Russell Wilson trade (2022):
    - Broncos gave: QB Russell Wilson (33, 83 OVR), 5th rounder
    - Seahawks gave: 2 first rounders, 2 second rounders, 1 fifth rounder
    """
    print_header("Scenario 1: Elite QB for Multiple First Round Picks")
    print("Simulating a blockbuster QB trade similar to Russell Wilson to Denver (2022)")
    print("\nTeam A (Contender) wants elite QB to win now")
    print("Team B (Rebuilding) trades franchise QB for draft capital")

    calc = TradeValueCalculator(current_year=2025)

    # Team A gives: Elite QB (age 30, 90 OVR, 4yr/$48M contract)
    qb = TradeAsset(
        asset_type=AssetType.PLAYER,
        player_id=1,
        player_name="Elite Franchise QB",
        position="quarterback",
        overall_rating=90,
        age=30,
        years_pro=8,
        contract_years_remaining=4,
        annual_cap_hit=48_000_000
    )
    qb.trade_value = calc.calculate_player_value(
        overall_rating=qb.overall_rating,
        position=qb.position,
        age=qb.age,
        contract_years_remaining=qb.contract_years_remaining,
        annual_cap_hit=qb.annual_cap_hit
    )

    # Team B gives: 2025 1st (#15), 2026 1st (#20 projected), 2025 2nd (#47), 2026 2nd (#51 projected)
    pick_2025_1st = DraftPick(round=1, year=2025, original_team_id=2, current_team_id=2)
    pick_2025_1st.overall_pick_projected = 15

    pick_2026_1st = DraftPick(round=1, year=2026, original_team_id=2, current_team_id=2)
    pick_2026_1st.overall_pick_projected = 20

    pick_2025_2nd = DraftPick(round=2, year=2025, original_team_id=2, current_team_id=2)
    pick_2025_2nd.overall_pick_projected = 47

    pick_2026_2nd = DraftPick(round=2, year=2026, original_team_id=2, current_team_id=2)
    pick_2026_2nd.overall_pick_projected = 51

    asset_2025_1st = TradeAsset(asset_type=AssetType.DRAFT_PICK, draft_pick=pick_2025_1st)
    asset_2025_1st.trade_value = calc.calculate_pick_value(pick_2025_1st)

    asset_2026_1st = TradeAsset(asset_type=AssetType.DRAFT_PICK, draft_pick=pick_2026_1st)
    asset_2026_1st.trade_value = calc.calculate_pick_value(pick_2026_1st)

    asset_2025_2nd = TradeAsset(asset_type=AssetType.DRAFT_PICK, draft_pick=pick_2025_2nd)
    asset_2025_2nd.trade_value = calc.calculate_pick_value(pick_2025_2nd)

    asset_2026_2nd = TradeAsset(asset_type=AssetType.DRAFT_PICK, draft_pick=pick_2026_2nd)
    asset_2026_2nd.trade_value = calc.calculate_pick_value(pick_2026_2nd)

    # Evaluate trade
    proposal = calc.evaluate_trade(
        team1_id=1,  # Team A (QB)
        team1_assets=[qb],
        team2_id=2,  # Team B (picks)
        team2_assets=[asset_2025_1st, asset_2026_1st, asset_2025_2nd, asset_2026_2nd]
    )

    print("\n--- TEAM A SENDS (Rebuilding Team) ---")
    print_asset_details(qb, calc)

    print("\n--- TEAM B SENDS (Contending Team) ---")
    for asset in [asset_2025_1st, asset_2026_1st, asset_2025_2nd, asset_2026_2nd]:
        print_asset_details(asset, calc)

    print_trade_summary(proposal)

    print("\n💡 Analysis:")
    print(f"   - Elite QB valued at {qb.trade_value:.1f} units")
    print(f"   - Four draft picks valued at {proposal.team2_total_value:.1f} units total")
    print(f"   - This is a {proposal.fairness_rating.value.replace('_', ' ')} trade")

    if proposal.is_acceptable():
        print("   ✓ Trade would likely be accepted by both teams")
    else:
        print("   ✗ Trade is too unbalanced - needs adjustment")


def scenario_2_star_wr_trade():
    """
    Scenario 2: Star WR for 1st + 2nd Round Picks

    Based on Tyreek Hill trade (2022):
    - Chiefs gave: WR Tyreek Hill (27, 95 OVR)
    - Dolphins gave: 2022 1st (#29), 2nd (#50), 4th, 2023 4th, 2023 6th
    """
    print_header("Scenario 2: Star WR for 1st + 2nd Round Picks")
    print("Simulating a star WR trade similar to Tyreek Hill to Miami (2022)")
    print("\nTeam A (Rebuilding) trades elite WR before contract expires")
    print("Team B (Contender) gets missing piece for Super Bowl run")

    calc = TradeValueCalculator(current_year=2025)

    # Team A gives: Star WR (age 27, 94 OVR, 1yr left on rookie deal)
    wr = TradeAsset(
        asset_type=AssetType.PLAYER,
        player_id=2,
        player_name="Elite WR1",
        position="wide_receiver",
        overall_rating=94,
        age=27,
        years_pro=5,
        contract_years_remaining=1,
        annual_cap_hit=18_000_000
    )
    wr.trade_value = calc.calculate_player_value(
        overall_rating=wr.overall_rating,
        position=wr.position,
        age=wr.age,
        contract_years_remaining=wr.contract_years_remaining,
        annual_cap_hit=wr.annual_cap_hit
    )

    # Team B gives: 2025 1st (#29), 2025 2nd (#50)
    pick_late_1st = DraftPick(round=1, year=2025, original_team_id=2, current_team_id=2)
    pick_late_1st.overall_pick_projected = 29

    pick_2nd = DraftPick(round=2, year=2025, original_team_id=2, current_team_id=2)
    pick_2nd.overall_pick_projected = 50

    asset_1st = TradeAsset(asset_type=AssetType.DRAFT_PICK, draft_pick=pick_late_1st)
    asset_1st.trade_value = calc.calculate_pick_value(pick_late_1st)

    asset_2nd = TradeAsset(asset_type=AssetType.DRAFT_PICK, draft_pick=pick_2nd)
    asset_2nd.trade_value = calc.calculate_pick_value(pick_2nd)

    # Evaluate trade
    proposal = calc.evaluate_trade(
        team1_id=1,  # Team A (WR)
        team1_assets=[wr],
        team2_id=2,  # Team B (picks)
        team2_assets=[asset_1st, asset_2nd]
    )

    print("\n--- TEAM A SENDS (Rebuilding Team) ---")
    print_asset_details(wr, calc)

    print("\n--- TEAM B SENDS (Contending Team) ---")
    print_asset_details(asset_1st, calc)
    print_asset_details(asset_2nd, calc)

    print_trade_summary(proposal)

    print("\n💡 Analysis:")
    print(f"   - Elite WR in prime valued at {wr.trade_value:.1f} units")
    print(f"   - Late 1st + 2nd round picks valued at {proposal.team2_total_value:.1f} units total")
    print(f"   - Contract status matters: only 1 year remaining reduces value")

    if proposal.is_acceptable():
        print("   ✓ Trade is fair - both teams get value")
    else:
        winner = proposal.get_winning_team()
        print(f"   ! Team {winner} gets better value in this trade")


def scenario_3_trade_up():
    """
    Scenario 3: Draft Position Trade-Up

    Team trading up 10 spots in 1st round (pick 20 → pick 10)
    Classic draft day trade for potential franchise QB
    """
    print_header("Scenario 3: Draft Position Trade-Up")
    print("Simulating a team trading up for a franchise QB in the draft")
    print("\nTeam A (Pick #20) trades up to secure QB prospect")
    print("Team B (Pick #10) moves down to accumulate picks")

    calc = TradeValueCalculator(current_year=2025)

    # Team A gives: Pick #20, Pick #51 (2nd round), 2026 1st (#25 projected)
    pick_20 = DraftPick(round=1, year=2025, original_team_id=1, current_team_id=1)
    pick_20.overall_pick_projected = 20

    pick_51 = DraftPick(round=2, year=2025, original_team_id=1, current_team_id=1)
    pick_51.overall_pick_projected = 51

    pick_2026 = DraftPick(round=1, year=2026, original_team_id=1, current_team_id=1)
    pick_2026.overall_pick_projected = 25

    asset_20 = TradeAsset(asset_type=AssetType.DRAFT_PICK, draft_pick=pick_20)
    asset_20.trade_value = calc.calculate_pick_value(pick_20)

    asset_51 = TradeAsset(asset_type=AssetType.DRAFT_PICK, draft_pick=pick_51)
    asset_51.trade_value = calc.calculate_pick_value(pick_51)

    asset_2026 = TradeAsset(asset_type=AssetType.DRAFT_PICK, draft_pick=pick_2026)
    asset_2026.trade_value = calc.calculate_pick_value(pick_2026)

    # Team B gives: Pick #10
    pick_10 = DraftPick(round=1, year=2025, original_team_id=2, current_team_id=2)
    pick_10.overall_pick_projected = 10

    asset_10 = TradeAsset(asset_type=AssetType.DRAFT_PICK, draft_pick=pick_10)
    asset_10.trade_value = calc.calculate_pick_value(pick_10)

    # Evaluate trade
    proposal = calc.evaluate_trade(
        team1_id=1,  # Team A (trading up)
        team1_assets=[asset_20, asset_51, asset_2026],
        team2_id=2,  # Team B (trading down)
        team2_assets=[asset_10]
    )

    print("\n--- TEAM A SENDS (Trading Up from #20 → #10) ---")
    print_asset_details(asset_20, calc)
    print_asset_details(asset_51, calc)
    print_asset_details(asset_2026, calc)

    print("\n--- TEAM B SENDS (Trading Down from #10 → #20) ---")
    print_asset_details(asset_10, calc)

    print_trade_summary(proposal)

    print("\n💡 Analysis:")
    print(f"   - Pick #10 valued at {asset_10.trade_value:.1f} units")
    print(f"   - Three picks (#20, #51, 2026 1st) valued at {proposal.team1_total_value:.1f} units total")
    print(f"   - Cost to move up 10 spots: {proposal.team1_total_value - asset_10.trade_value:.1f} units")
    print(f"   - Future pick discounted by 5% per year")

    if proposal.is_acceptable():
        print("   ✓ Fair trade-up compensation following Jimmy Johnson chart")
    else:
        print("   ! Trade needs adjustment - pick values don't align")


def scenario_4_salary_dump():
    """
    Scenario 4: Salary Dump Trade

    Team dumps aging player with bad contract for draft pick compensation
    """
    print_header("Scenario 4: Salary Dump Trade")
    print("Simulating a team dumping a bad contract for cap relief")
    print("\nTeam A (Over cap) needs to shed salary")
    print("Team B (Under cap) has space and wants draft compensation")

    calc = TradeValueCalculator(current_year=2025)

    # Team A gives: Aging veteran (age 33, 78 OVR, 3yr/$24M left - bad contract)
    # Plus 2025 3rd round pick as compensation
    veteran = TradeAsset(
        asset_type=AssetType.PLAYER,
        player_id=3,
        player_name="Aging Veteran LB",
        position="linebacker",
        overall_rating=78,
        age=33,
        years_pro=11,
        contract_years_remaining=3,
        annual_cap_hit=24_000_000  # Overpaid
    )
    veteran.trade_value = calc.calculate_player_value(
        overall_rating=veteran.overall_rating,
        position=veteran.position,
        age=veteran.age,
        contract_years_remaining=veteran.contract_years_remaining,
        annual_cap_hit=veteran.annual_cap_hit
    )

    # Compensation pick
    pick_3rd = DraftPick(round=3, year=2025, original_team_id=1, current_team_id=1)
    pick_3rd.overall_pick_projected = 85

    asset_3rd = TradeAsset(asset_type=AssetType.DRAFT_PICK, draft_pick=pick_3rd)
    asset_3rd.trade_value = calc.calculate_pick_value(pick_3rd)

    # Team B gives: 2025 7th round pick (minimal value, salary cap absorber)
    pick_7th = DraftPick(round=7, year=2025, original_team_id=2, current_team_id=2)
    pick_7th.overall_pick_projected = 235

    asset_7th = TradeAsset(asset_type=AssetType.DRAFT_PICK, draft_pick=pick_7th)
    asset_7th.trade_value = calc.calculate_pick_value(pick_7th)

    # Evaluate trade
    proposal = calc.evaluate_trade(
        team1_id=1,  # Team A (dumping salary)
        team1_assets=[veteran, asset_3rd],
        team2_id=2,  # Team B (absorbing cap hit)
        team2_assets=[asset_7th]
    )

    print("\n--- TEAM A SENDS (Cap-Strapped Team) ---")
    print_asset_details(veteran, calc)
    print(f"    Cap Relief: ${veteran.annual_cap_hit / 1_000_000:.1f}M/yr")
    print_asset_details(asset_3rd, calc)

    print("\n--- TEAM B SENDS (Cap Space Team) ---")
    print_asset_details(asset_7th, calc)

    print_trade_summary(proposal)

    print("\n💡 Analysis:")
    print(f"   - Aging veteran with bad contract has negative value: {veteran.trade_value:.1f} units")
    print(f"   - 3rd round pick compensation: {asset_3rd.trade_value:.1f} units")
    print(f"   - Net value for Team A: {proposal.team1_total_value:.1f} units")
    print(f"   - Team B gets draft pick upgrade for absorbing cap hit")

    if proposal.is_acceptable():
        print("   ✓ Fair salary dump - both teams benefit")
    else:
        print("   ! More compensation needed to balance the trade")


def scenario_5_blockbuster():
    """
    Scenario 5: Multi-Asset Blockbuster Trade

    Complex 3-for-3 trade involving multiple players and picks
    """
    print_header("Scenario 5: Multi-Asset Blockbuster Trade")
    print("Simulating a complex multi-player, multi-pick trade")
    print("\nTeam A (Contender) goes all-in for championship pieces")
    print("Team B (Rebuilding) trades veterans for youth and picks")

    calc = TradeValueCalculator(current_year=2025)

    # Team A gives: Young WR (25, 84 OVR), 2025 1st (#22), 2026 2nd (#55 projected)
    young_wr = TradeAsset(
        asset_type=AssetType.PLAYER,
        player_id=4,
        player_name="Young WR2",
        position="wide_receiver",
        overall_rating=84,
        age=25,
        years_pro=3,
        contract_years_remaining=2,
        annual_cap_hit=8_000_000
    )
    young_wr.trade_value = calc.calculate_player_value(
        overall_rating=young_wr.overall_rating,
        position=young_wr.position,
        age=young_wr.age,
        contract_years_remaining=young_wr.contract_years_remaining,
        annual_cap_hit=young_wr.annual_cap_hit
    )

    pick_22 = DraftPick(round=1, year=2025, original_team_id=1, current_team_id=1)
    pick_22.overall_pick_projected = 22
    asset_22 = TradeAsset(asset_type=AssetType.DRAFT_PICK, draft_pick=pick_22)
    asset_22.trade_value = calc.calculate_pick_value(pick_22)

    pick_55_2026 = DraftPick(round=2, year=2026, original_team_id=1, current_team_id=1)
    pick_55_2026.overall_pick_projected = 55
    asset_55 = TradeAsset(asset_type=AssetType.DRAFT_PICK, draft_pick=pick_55_2026)
    asset_55.trade_value = calc.calculate_pick_value(pick_55_2026)

    # Team B gives: Star CB (28, 91 OVR), Edge Rusher (26, 87 OVR), 2025 4th (#120)
    star_cb = TradeAsset(
        asset_type=AssetType.PLAYER,
        player_id=5,
        player_name="Elite CB1",
        position="cornerback",
        overall_rating=91,
        age=28,
        years_pro=6,
        contract_years_remaining=2,
        annual_cap_hit=16_000_000
    )
    star_cb.trade_value = calc.calculate_player_value(
        overall_rating=star_cb.overall_rating,
        position=star_cb.position,
        age=star_cb.age,
        contract_years_remaining=star_cb.contract_years_remaining,
        annual_cap_hit=star_cb.annual_cap_hit
    )

    edge = TradeAsset(
        asset_type=AssetType.PLAYER,
        player_id=6,
        player_name="Solid Edge Rusher",
        position="edge_rusher",
        overall_rating=87,
        age=26,
        years_pro=4,
        contract_years_remaining=3,
        annual_cap_hit=14_000_000
    )
    edge.trade_value = calc.calculate_player_value(
        overall_rating=edge.overall_rating,
        position=edge.position,
        age=edge.age,
        contract_years_remaining=edge.contract_years_remaining,
        annual_cap_hit=edge.annual_cap_hit
    )

    pick_120 = DraftPick(round=4, year=2025, original_team_id=2, current_team_id=2)
    pick_120.overall_pick_projected = 120
    asset_120 = TradeAsset(asset_type=AssetType.DRAFT_PICK, draft_pick=pick_120)
    asset_120.trade_value = calc.calculate_pick_value(pick_120)

    # Evaluate trade
    proposal = calc.evaluate_trade(
        team1_id=1,  # Team A (contender)
        team1_assets=[young_wr, asset_22, asset_55],
        team2_id=2,  # Team B (rebuilding)
        team2_assets=[star_cb, edge, asset_120]
    )

    print("\n--- TEAM A SENDS (Contending Team) ---")
    print_asset_details(young_wr, calc)
    print_asset_details(asset_22, calc)
    print_asset_details(asset_55, calc)

    print("\n--- TEAM B SENDS (Rebuilding Team) ---")
    print_asset_details(star_cb, calc)
    print_asset_details(edge, calc)
    print_asset_details(asset_120, calc)

    print_trade_summary(proposal)

    print("\n💡 Analysis:")
    print(f"   - Team A gets: Elite CB ({star_cb.trade_value:.1f}) + Edge ({edge.trade_value:.1f}) = {proposal.team2_total_value:.1f} total")
    print(f"   - Team B gets: Young WR ({young_wr.trade_value:.1f}) + Picks ({asset_22.trade_value + asset_55.trade_value:.1f}) = {proposal.team1_total_value:.1f} total")
    print(f"   - Team A trades future for win-now pieces")
    print(f"   - Team B gets younger and adds draft capital")

    if proposal.is_acceptable():
        print("   ✓ Blockbuster trade works for both teams' timelines")
    else:
        winner = proposal.get_winning_team()
        print(f"   ! Team {winner} gets significantly better value")


def interactive_calculator():
    """
    Interactive mode: User can input their own trade scenarios
    """
    print_header("Interactive Trade Calculator")
    print("Build your own trade and see if it's fair!\n")

    calc = TradeValueCalculator(current_year=2025)

    while True:
        print("\n" + "-" * 80)
        print("What would you like to evaluate?")
        print("  1. Single player value")
        print("  2. Single draft pick value")
        print("  3. Complete trade proposal")
        print("  4. Return to main menu")
        print("-" * 80)

        choice = input("\nEnter choice (1-4): ").strip()

        if choice == "1":
            evaluate_single_player(calc)
        elif choice == "2":
            evaluate_single_pick(calc)
        elif choice == "3":
            evaluate_trade_proposal(calc)
        elif choice == "4":
            break
        else:
            print("Invalid choice. Please enter 1-4.")


def evaluate_single_player(calc: TradeValueCalculator):
    """Evaluate a single player's trade value"""
    print("\n--- Player Valuation ---")

    try:
        overall = int(input("Overall rating (40-99): ").strip())
        age = int(input("Age (21-40): ").strip())

        print("\nPosition options:")
        print("  quarterback, running_back, wide_receiver, tight_end")
        print("  left_tackle, right_tackle, guard, center")
        print("  edge_rusher, interior_lineman, linebacker")
        print("  cornerback, safety")
        position = input("Position: ").strip().lower()

        contract_years = input("Contract years remaining (optional, press Enter to skip): ").strip()
        cap_hit = input("Annual cap hit in millions (optional, press Enter to skip): ").strip()

        contract_years_val = int(contract_years) if contract_years else None
        cap_hit_val = int(float(cap_hit) * 1_000_000) if cap_hit else None

        value = calc.calculate_player_value(
            overall_rating=overall,
            position=position,
            age=age,
            contract_years_remaining=contract_years_val,
            annual_cap_hit=cap_hit_val
        )

        print(f"\n✓ Trade Value: {value:.1f} units")

        # Provide context
        if value > 600:
            print("   → Elite franchise cornerstone (top 5 at position)")
        elif value > 400:
            print("   → Star player (top 10-15 at position)")
        elif value > 200:
            print("   → Quality starter (above average)")
        elif value > 100:
            print("   → Solid starter (average)")
        elif value > 50:
            print("   → Depth player / rotational starter")
        else:
            print("   → Backup / special teamer")

    except ValueError as e:
        print(f"\n✗ Invalid input: {e}")
    except Exception as e:
        print(f"\n✗ Error calculating value: {e}")


def evaluate_single_pick(calc: TradeValueCalculator):
    """Evaluate a single draft pick's trade value"""
    print("\n--- Draft Pick Valuation ---")

    try:
        round_num = int(input("Round (1-7): ").strip())
        year = int(input("Year (2025-2030): ").strip())
        overall = int(input("Projected overall pick number (1-262): ").strip())

        pick = DraftPick(
            round=round_num,
            year=year,
            original_team_id=1,
            current_team_id=1
        )
        pick.overall_pick_projected = overall

        value = calc.calculate_pick_value(pick)

        print(f"\n✓ Trade Value: {value:.1f} units")

        # Show Jimmy Johnson chart base value
        base_value = calc.draft_pick_values.get(overall, 0)
        print(f"   Jimmy Johnson Chart Value: {base_value:.1f} units")

        if year > calc.current_year:
            years_out = year - calc.current_year
            discount = (0.95 ** years_out)
            print(f"   Future Discount: {discount:.2%} ({years_out} year{'s' if years_out > 1 else ''} out)")

        # Provide context
        if overall <= 10:
            print("   → Elite prospect territory (franchise QB/LT/Edge)")
        elif overall <= 32:
            print("   → First round pick (potential starter/star)")
        elif overall <= 64:
            print("   → Second round pick (likely starter)")
        elif overall <= 100:
            print("   → Third round pick (rotational player/backup)")
        else:
            print("   → Late round pick (depth/special teams)")

    except ValueError as e:
        print(f"\n✗ Invalid input: {e}")
    except Exception as e:
        print(f"\n✗ Error calculating value: {e}")


def evaluate_trade_proposal(calc: TradeValueCalculator):
    """Evaluate a complete trade proposal (simplified version)"""
    print("\n--- Trade Proposal Evaluation ---")
    print("Note: This is a simplified version. For complex trades, use the API directly.\n")

    print("This would build a complete trade step-by-step.")
    print("For now, try the 5 pre-built scenarios from the main menu!")
    print("(Full interactive trade builder coming in next update)")


def main_menu():
    """Main menu for the demo"""
    while True:
        print_header("Trade Value Calculator - Interactive Demo")
        print("Choose a scenario to explore:")
        print("\n  PRE-BUILT SCENARIOS:")
        print("    1. Elite QB for Multiple First Round Picks (Russell Wilson style)")
        print("    2. Star WR for 1st + 2nd Round Picks (Tyreek Hill style)")
        print("    3. Draft Position Trade-Up (Moving up 10 spots)")
        print("    4. Salary Dump Trade (Bad contract + pick compensation)")
        print("    5. Multi-Asset Blockbuster (3-for-3 trade)")
        print("\n  INTERACTIVE MODE:")
        print("    6. Build Your Own Trade")
        print("\n  OTHER:")
        print("    7. Exit")
        print("-" * 80)

        choice = input("\nEnter choice (1-7): ").strip()

        if choice == "1":
            scenario_1_elite_qb_trade()
            input("\nPress Enter to continue...")
        elif choice == "2":
            scenario_2_star_wr_trade()
            input("\nPress Enter to continue...")
        elif choice == "3":
            scenario_3_trade_up()
            input("\nPress Enter to continue...")
        elif choice == "4":
            scenario_4_salary_dump()
            input("\nPress Enter to continue...")
        elif choice == "5":
            scenario_5_blockbuster()
            input("\nPress Enter to continue...")
        elif choice == "6":
            interactive_calculator()
        elif choice == "7":
            print("\nThanks for using the Trade Value Calculator!")
            break
        else:
            print("\nInvalid choice. Please enter 1-7.")


if __name__ == "__main__":
    print("\n" + "🏈" * 40)
    print("\n  NFL TRADE VALUE CALCULATOR - INTERACTIVE DEMO")
    print("  Phase 1.2: AI Transaction System Development")
    print("\n" + "🏈" * 40)

    main_menu()
