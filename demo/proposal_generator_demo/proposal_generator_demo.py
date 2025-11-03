#!/usr/bin/env python3
"""
Trade Proposal Generator Interactive Demo

Demonstrates the complete trade proposal generation system with realistic NFL scenarios.
Shows league-wide scanning, fair value construction, GM personality filtering, and validation.

IMPORTANT: This demo requires an initialized database with player rosters loaded.
           Run 'PYTHONPATH=src python demo/full_season_demo/full_season_sim.py' first
           to create a dynasty with rosters, or use an existing dynasty database.

Usage:
    PYTHONPATH=src python demo/proposal_generator_demo/proposal_generator_demo.py

Features Demonstrated:
- League-wide scanning (32 teams, ~1,696 players)
- Fair value construction (greedy algorithm: 1-for-1 → 2-for-1 → 3-for-1)
- GM personality filters (trade_frequency, star_chasing, cap_management, veteran_preference)
- Validation pipeline (6 checks)
- Different team contexts (contender, rebuilder, middling)
- Multiple need scenarios (CRITICAL, HIGH, MEDIUM urgency)
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from transactions.trade_proposal_generator import TradeProposalGenerator, TeamContext
from transactions.trade_value_calculator import TradeValueCalculator
from offseason.team_needs_analyzer import NeedUrgency
from team_management.gm_archetype import GMArchetype
import os


def check_database_initialization() -> bool:
    """Check if database exists and has rosters loaded."""
    db_path = "data/database/nfl_simulation.db"

    if not os.path.exists(db_path):
        print("\n" + "=" * 80)
        print("  ⚠️  DATABASE NOT FOUND")
        print("=" * 80)
        print("\n  The database file does not exist. You need to initialize a dynasty first.")
        print("\n  To initialize a new dynasty with rosters:")
        print("    PYTHONPATH=src python demo/full_season_demo/full_season_sim.py")
        print("\n  Or specify an existing database path in the demo script.")
        print("=" * 80 + "\n")
        return False

    return True


def print_database_requirement_notice() -> None:
    """Print notice about database requirements for this demo."""
    print("\n" + "!" * 80)
    print("  NOTICE: This demo requires an initialized database with player rosters")
    print("!" * 80)
    print("\n  Unlike the Trade Value Calculator demo (Phase 1.2), the Proposal Generator")
    print("  performs real league-wide scanning across all 32 NFL teams to identify")
    print("  tradeable surplus assets.")
    print("\n  If you see 'No roster found' errors, you need to:")
    print("    1. Run: PYTHONPATH=src python demo/full_season_demo/full_season_sim.py")
    print("    2. This will create a dynasty and load all team rosters")
    print("    3. Then re-run this demo with the same dynasty")
    print("\n  OR")
    print("    4. Use an existing dynasty by updating database_path in this script")
    print("!" * 80 + "\n")


def print_header(text: str) -> None:
    """Print formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def print_subheader(text: str) -> None:
    """Print formatted subsection header."""
    print(f"\n--- {text} ---")


def print_proposals(proposals: list, title: str = "Generated Proposals") -> None:
    """Print formatted proposal list."""
    print_subheader(title)

    if not proposals:
        print("  ❌ No viable proposals found")
        return

    print(f"  ✅ Found {len(proposals)} proposal(s)\n")

    for i, proposal in enumerate(proposals, 1):
        print(f"  PROPOSAL #{i}:")
        print(f"  {'─' * 76}")

        # Team 1 (proposing team) assets
        team1_assets_str = ", ".join(str(a) for a in proposal.team1_assets)
        print(f"  Team {proposal.team1_id} sends: {team1_assets_str}")
        print(f"    Total Value: {proposal.team1_total_value:.1f} units")

        # Team 2 (receiving proposal) assets
        team2_assets_str = ", ".join(str(a) for a in proposal.team2_assets)
        print(f"  Team {proposal.team2_id} sends: {team2_assets_str}")
        print(f"    Total Value: {proposal.team2_total_value:.1f} units")

        # Fairness analysis
        print(f"\n  Value Ratio: {proposal.value_ratio:.3f} ({proposal.fairness_rating.value})")
        print(f"  Acceptable: {'✓ YES' if proposal.is_acceptable() else '✗ NO'}")
        print(f"  Cap Valid: {'✓ YES' if proposal.passes_cap_validation else '✗ NO'}")
        print()


def create_conservative_gm() -> GMArchetype:
    """Create conservative GM archetype."""
    return GMArchetype(
        name="Conservative GM",
        description="Conservative GM who rarely trades and is cap conscious",
        trade_frequency=0.3,      # Rarely trades
        star_chasing=0.2,         # Avoids expensive stars
        cap_management=0.8,       # Very cap conscious
        veteran_preference=0.5,   # Neutral on age
        risk_tolerance=0.3,
        win_now_mentality=0.3,
        draft_pick_value=0.6,
        loyalty=0.7
    )


def create_balanced_gm() -> GMArchetype:
    """Create balanced GM archetype."""
    return GMArchetype(
        name="Balanced GM",
        description="Balanced GM with moderate approach to all aspects",
        trade_frequency=0.5,      # Moderate trading
        star_chasing=0.5,         # Balanced approach
        cap_management=0.5,       # Balanced cap management
        veteran_preference=0.5,   # Neutral on age
        risk_tolerance=0.5,
        win_now_mentality=0.5,
        draft_pick_value=0.5,
        loyalty=0.5
    )


def create_aggressive_gm() -> GMArchetype:
    """Create aggressive GM archetype."""
    return GMArchetype(
        name="Aggressive GM",
        description="Aggressive GM who trades frequently and targets stars",
        trade_frequency=0.9,      # Trades frequently
        star_chasing=0.8,         # Targets elite players
        cap_management=0.3,       # Less concerned with cap
        veteran_preference=0.7,   # Prefers proven vets
        risk_tolerance=0.8,
        win_now_mentality=0.9,
        draft_pick_value=0.3,
        loyalty=0.3
    )


def create_star_chaser_gm() -> GMArchetype:
    """Create star-chasing GM archetype."""
    return GMArchetype(
        name="Star Chaser GM",
        description="GM who heavily targets star players over balanced roster",
        trade_frequency=0.7,
        star_chasing=0.95,        # Heavily targets stars (85+ OVR)
        cap_management=0.2,       # Willing to pay premium
        veteran_preference=0.6,
        risk_tolerance=0.7,
        win_now_mentality=0.9,
        draft_pick_value=0.3,     # Prefers proven talent
        loyalty=0.4
    )


def create_youth_gm() -> GMArchetype:
    """Create youth-focused GM archetype."""
    return GMArchetype(
        name="Youth Movement GM",
        description="GM focused on building through youth and draft",
        trade_frequency=0.6,
        star_chasing=0.2,         # Avoids expensive stars
        cap_management=0.7,       # Cap conscious
        veteran_preference=0.1,   # Strongly prefers youth (<29)
        risk_tolerance=0.6,
        win_now_mentality=0.2,    # Long-term focus
        draft_pick_value=0.8,     # Builds through draft
        loyalty=0.6
    )


def demo_contender_scenario() -> None:
    """Demo: Contending team seeking impact player for playoff push."""
    print_header("SCENARIO 1: Contender Seeking Impact Player")

    print("\n  Team Profile:")
    print("    Record: 8-1 (contending for playoffs)")
    print("    Cap Space: $25M")
    print("    Critical Need: Elite pass rusher (DE)")
    print("    GM Style: Aggressive (win-now mode)")

    # Create components (using actual database)
    db_path = "data/database/nfl_simulation.db"
    dynasty_id = "default_dynasty"  # Use default dynasty, or specify custom
    calculator = TradeValueCalculator(db_path, dynasty_id)
    generator = TradeProposalGenerator(db_path, dynasty_id, calculator)

    # Contender context
    context = TeamContext(
        team_id=22,  # Contending team
        wins=8,
        losses=1,
        cap_space=25_000_000,
        season="regular"
    )

    # Aggressive GM
    gm = create_aggressive_gm()

    # Critical need for pass rusher
    needs = [
        {'position': 'defensive_end', 'urgency': NeedUrgency.CRITICAL}
    ]

    print("\n  Scanning league for elite defensive ends...")
    proposals = generator.generate_trade_proposals(
        team_id=22,
        gm_archetype=gm,
        team_context=context,
        needs=needs,
        season=2025
    )

    print_proposals(proposals, "Trade Proposals (Sorted by Fairness)")


def demo_rebuilder_scenario() -> None:
    """Demo: Rebuilding team trading veterans for youth."""
    print_header("SCENARIO 2: Rebuilder Trading Veterans for Youth")

    print("\n  Team Profile:")
    print("    Record: 1-6 (rebuilding)")
    print("    Cap Space: $45M")
    print("    Strategy: Trade veterans, acquire youth/picks")
    print("    GM Style: Youth Movement (long-term focus)")

    # Create components (using actual database)
    db_path = "data/database/nfl_simulation.db"
    dynasty_id = "default_dynasty"  # Use default dynasty, or specify custom
    calculator = TradeValueCalculator(db_path, dynasty_id)
    generator = TradeProposalGenerator(db_path, dynasty_id, calculator)

    # Rebuilder context
    context = TeamContext(
        team_id=15,  # Rebuilding team
        wins=1,
        losses=6,
        cap_space=45_000_000,
        season="regular"
    )

    # Youth-focused GM
    gm = create_youth_gm()

    # Multiple needs (willing to trade for various positions)
    needs = [
        {'position': 'quarterback', 'urgency': NeedUrgency.HIGH},
        {'position': 'wide_receiver', 'urgency': NeedUrgency.HIGH},
        {'position': 'offensive_line', 'urgency': NeedUrgency.MEDIUM}
    ]

    print("\n  Scanning league for young talent...")
    proposals = generator.generate_trade_proposals(
        team_id=15,
        gm_archetype=gm,
        team_context=context,
        needs=needs,
        season=2025
    )

    print_proposals(proposals, "Trade Proposals (Youth-Focused)")


def demo_star_chaser_scenario() -> None:
    """Demo: Star-chasing GM targeting elite players."""
    print_header("SCENARIO 3: Star Chaser Targeting Elite Players")

    print("\n  Team Profile:")
    print("    Record: 5-2 (competing)")
    print("    Cap Space: $20M")
    print("    Target: Elite WR (85+ OVR)")
    print("    GM Style: Star Chaser (targets big names)")

    # Create components (using actual database)
    db_path = "data/database/nfl_simulation.db"
    dynasty_id = "default_dynasty"  # Use default dynasty, or specify custom
    calculator = TradeValueCalculator(db_path, dynasty_id)
    generator = TradeProposalGenerator(db_path, dynasty_id, calculator)

    # Competing team context
    context = TeamContext(
        team_id=18,
        wins=5,
        losses=2,
        cap_space=20_000_000,
        season="regular"
    )

    # Star-chasing GM
    gm = create_star_chaser_gm()

    # Need elite receiver
    needs = [
        {'position': 'wide_receiver', 'urgency': NeedUrgency.CRITICAL}
    ]

    print("\n  Scanning league for elite wide receivers (85+ OVR)...")
    proposals = generator.generate_trade_proposals(
        team_id=18,
        gm_archetype=gm,
        team_context=context,
        needs=needs,
        season=2025
    )

    print_proposals(proposals, "Trade Proposals (Elite Players Only)")


def demo_conservative_gm_scenario() -> None:
    """Demo: Conservative GM with limited trade activity."""
    print_header("SCENARIO 4: Conservative GM (Limited Activity)")

    print("\n  Team Profile:")
    print("    Record: 4-3 (middling)")
    print("    Cap Space: $15M")
    print("    Need: Linebacker depth")
    print("    GM Style: Conservative (rarely trades)")

    # Create components (using actual database)
    db_path = "data/database/nfl_simulation.db"
    dynasty_id = "default_dynasty"  # Use default dynasty, or specify custom
    calculator = TradeValueCalculator(db_path, dynasty_id)
    generator = TradeProposalGenerator(db_path, dynasty_id, calculator)

    # Middling team context
    context = TeamContext(
        team_id=10,
        wins=4,
        losses=3,
        cap_space=15_000_000,
        season="regular"
    )

    # Conservative GM
    gm = create_conservative_gm()

    # High need for linebacker
    needs = [
        {'position': 'linebacker', 'urgency': NeedUrgency.HIGH}
    ]

    print("\n  Scanning league (conservative GM - expect fewer proposals)...")
    proposals = generator.generate_trade_proposals(
        team_id=10,
        gm_archetype=gm,
        team_context=context,
        needs=needs,
        season=2025
    )

    print_proposals(proposals, "Trade Proposals (Conservative Approach)")

    print("\n  Note: Conservative GMs generate fewer proposals due to:")
    print("    - Low trade_frequency (0.3) → max 1-2 proposals")
    print("    - High cap_management (0.8) → strict cap limits")
    print("    - Low star_chasing (0.2) → avoids expensive players")


def demo_multiple_needs_scenario() -> None:
    """Demo: Team with multiple needs across positions."""
    print_header("SCENARIO 5: Multiple Team Needs")

    print("\n  Team Profile:")
    print("    Record: 3-4 (struggling)")
    print("    Cap Space: $30M")
    print("    Multiple Needs: CB (CRITICAL), LB (HIGH), OL (MEDIUM)")
    print("    GM Style: Balanced")

    # Create components (using actual database)
    db_path = "data/database/nfl_simulation.db"
    dynasty_id = "default_dynasty"  # Use default dynasty, or specify custom
    calculator = TradeValueCalculator(db_path, dynasty_id)
    generator = TradeProposalGenerator(db_path, dynasty_id, calculator)

    # Struggling team context
    context = TeamContext(
        team_id=12,
        wins=3,
        losses=4,
        cap_space=30_000_000,
        season="regular"
    )

    # Balanced GM
    gm = create_balanced_gm()

    # Multiple needs at different urgency levels
    needs = [
        {'position': 'cornerback', 'urgency': NeedUrgency.CRITICAL},
        {'position': 'linebacker', 'urgency': NeedUrgency.HIGH},
        {'position': 'offensive_line', 'urgency': NeedUrgency.MEDIUM}
    ]

    print("\n  Scanning league for multiple positions...")
    print("  Note: Generator prioritizes CRITICAL and HIGH needs (ignores MEDIUM)")
    proposals = generator.generate_trade_proposals(
        team_id=12,
        gm_archetype=gm,
        team_context=context,
        needs=needs,
        season=2025
    )

    print_proposals(proposals, "Trade Proposals (Multiple Needs)")


def demo_gm_personality_comparison() -> None:
    """Demo: Same scenario with different GM personalities."""
    print_header("SCENARIO 6: GM Personality Impact (Same Team, Different GMs)")

    print("\n  Base Team Profile:")
    print("    Record: 6-2")
    print("    Cap Space: $22M")
    print("    Need: Wide Receiver (HIGH urgency)")
    print("\n  Testing 3 GM Personalities:")

    # Create components (using actual database)
    db_path = "data/database/nfl_simulation.db"
    dynasty_id = "default_dynasty"  # Use default dynasty, or specify custom
    calculator = TradeValueCalculator(db_path, dynasty_id)
    generator = TradeProposalGenerator(db_path, dynasty_id, calculator)

    # Same team context for all GMs
    context = TeamContext(
        team_id=20,
        wins=6,
        losses=2,
        cap_space=22_000_000,
        season="regular"
    )

    # Same need for all GMs
    needs = [
        {'position': 'wide_receiver', 'urgency': NeedUrgency.HIGH}
    ]

    # Test with conservative GM
    print_subheader("A) Conservative GM")
    print("  Traits: Low trade frequency (0.3), avoids stars, cap conscious")
    conservative_gm = create_conservative_gm()
    conservative_proposals = generator.generate_trade_proposals(
        team_id=20,
        gm_archetype=conservative_gm,
        team_context=context,
        needs=needs,
        season=2025
    )
    print(f"  Result: {len(conservative_proposals)} proposal(s)")

    # Test with balanced GM
    print_subheader("B) Balanced GM")
    print("  Traits: Moderate in all aspects (0.5 across the board)")
    balanced_gm = create_balanced_gm()
    balanced_proposals = generator.generate_trade_proposals(
        team_id=20,
        gm_archetype=balanced_gm,
        team_context=context,
        needs=needs,
        season=2025
    )
    print(f"  Result: {len(balanced_proposals)} proposal(s)")

    # Test with aggressive GM
    print_subheader("C) Aggressive GM")
    print("  Traits: High trade frequency (0.9), targets stars, less cap conscious")
    aggressive_gm = create_aggressive_gm()
    aggressive_proposals = generator.generate_trade_proposals(
        team_id=20,
        gm_archetype=aggressive_gm,
        team_context=context,
        needs=needs,
        season=2025
    )
    print(f"  Result: {len(aggressive_proposals)} proposal(s)")

    print("\n  Analysis:")
    print(f"    Conservative: {len(conservative_proposals)} proposals (max 1-2 due to low frequency)")
    print(f"    Balanced:     {len(balanced_proposals)} proposals (max 2-3)")
    print(f"    Aggressive:   {len(aggressive_proposals)} proposals (max 4-5)")
    print("\n  Conclusion: GM personality significantly impacts proposal generation!")


def print_system_info() -> None:
    """Print system capabilities and architecture info."""
    print_header("Trade Proposal Generator - System Overview")

    print("\n  7-Step Generation Pipeline:")
    print("    1. Filter Priority Needs (CRITICAL + HIGH urgency only)")
    print("    2. League-Wide Scan (all 32 teams, filter by position)")
    print("    3. Identify Surplus Assets (beyond position minimums)")
    print("    4. Construct Fair Value (greedy: 1-for-1 → 2-for-1 → 3-for-1)")
    print("    5. Apply GM Filters (frequency, star chasing, cap, veteran pref)")
    print("    6. Validation Pipeline (6 checks)")
    print("    7. Sort by Priority (fairness proximity + simplicity)")

    print("\n  Performance Metrics:")
    print("    - League-Wide Scan: <150ms (32 teams × ~53 players)")
    print("    - Single Team Eval: <50ms average")
    print("    - Max Proposals: 5 per call")
    print("    - Value Ratio Range: 0.80 - 1.20 (fair trades only)")

    print("\n  GM Personality Filters:")
    print("    1. Trade Frequency: Controls max proposals (conservative=1, aggressive=4)")
    print("    2. Star Chasing: Targets 85+ OVR (high) or avoids 88+ OVR (low)")
    print("    3. Cap Management: Max cap consumption (50%-80% based on value)")
    print("    4. Veteran Preference: Age preferences (27+ or <29)")

    print("\n  Integration with Phase 1.3:")
    print("    ✓ TradeValueCalculator: Objective asset valuation")
    print("    ✓ TradeEvaluator: Compatible proposal structure")
    print("    ✓ NegotiatorEngine: Ready for multi-round negotiation")


def main() -> None:
    """Run interactive demo scenarios."""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "TRADE PROPOSAL GENERATOR DEMO" + " " * 29 + "║")
    print("║" + " " * 25 + "Phase 1.4 Complete" + " " * 34 + "║")
    print("╚" + "═" * 78 + "╝")

    # Check if database is initialized
    if not check_database_initialization():
        return

    # Print database requirement notice
    print_database_requirement_notice()

    # Print system overview
    print_system_info()

    # Run all scenarios
    demo_contender_scenario()
    demo_rebuilder_scenario()
    demo_star_chaser_scenario()
    demo_conservative_gm_scenario()
    demo_multiple_needs_scenario()
    demo_gm_personality_comparison()

    # Final summary
    print_header("Demo Complete")
    print("\n  All 6 scenarios demonstrated:")
    print("    ✓ Scenario 1: Contender seeking impact player")
    print("    ✓ Scenario 2: Rebuilder trading veterans")
    print("    ✓ Scenario 3: Star chaser targeting elite players")
    print("    ✓ Scenario 4: Conservative GM with limited activity")
    print("    ✓ Scenario 5: Multiple team needs")
    print("    ✓ Scenario 6: GM personality comparison")

    print("\n  Key Takeaways:")
    print("    • League-wide scanning finds best trade partners across all 32 teams")
    print("    • Fair value construction ensures balanced trades (0.80-1.20 ratio)")
    print("    • GM personality significantly impacts proposal generation")
    print("    • System handles diverse scenarios (contenders, rebuilders, balanced teams)")
    print("    • Validation pipeline ensures all proposals are executable")

    print("\n  Next Steps:")
    print("    • Phase 1.5: Transaction AI Manager (daily orchestration)")
    print("    • Phase 2.0: Draft pick integration")
    print("    • Phase 3.0: Multi-team trades (3+ teams)")
    print("    • Phase 4.0: Counter-offer generation")

    print("\n  For more information:")
    print("    • Documentation: PHASE_1_4_COMPLETE.md")
    print("    • Test Suite: tests/transactions/test_trade_proposal_generator.py (56 tests)")
    print("    • Architecture: docs/plans/ai_transactions_plan.md")

    print("\n" + "=" * 80)
    print()


if __name__ == "__main__":
    main()
