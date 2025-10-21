"""
Franchise Tag AI Demo

Demonstrates Gap 4: AI evaluating franchise tag candidates for all 32 teams.
Shows how AI decides which players to tag based on value analysis.

Run: PYTHONPATH=src python demo/ai_logic/demo_franchise_tag_ai.py
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from offseason.offseason_controller import OffseasonController
from team_management.teams.team_loader import get_team_by_id


def print_separator(char="=", length=80):
    """Print a visual separator."""
    print(char * length)


def print_tag_candidate(candidate: dict, rank: int):
    """Pretty print a tag candidate."""
    print(f"\n   #{rank}. {candidate['player_name']} - {candidate['position'].upper()}")
    print(f"       Overall: {candidate['overall']} OVR")
    print(f"       Tag Cost: ${candidate['tag_cost']:,}")
    print(f"       Market AAV: ${candidate['market_value_aav']:.2f}M")
    print(f"       Value Score: {candidate['tag_value_score']:.2f}")
    print(f"       Team Need: {'Yes ✓' if candidate['is_team_need'] else 'No'}")
    print(f"       Recommendation: {candidate['recommendation']}")


def main():
    """Run franchise tag AI demo for all 32 teams."""
    print_separator()
    print("🏷️  FRANCHISE TAG AI DEMONSTRATION")
    print_separator()
    print("\nThis demo shows AI evaluating franchise tag candidates for NFL teams.")
    print("AI considers:")
    print("  • Tag cost vs market value (Gap 3: MarketValueCalculator)")
    print("  • Team positional needs (Gap 2: TeamNeedsAnalyzer)")
    print("  • Available salary cap space")
    print("  • Player quality and position value")
    print()

    # Initialize controller
    controller = OffseasonController(
        database_path="data/database/nfl_simulation.db",
        dynasty_id="phase2_testing",
        season_year=2025,
        user_team_id=7,  # Pittsburgh (won't be processed)
        enable_persistence=False,  # Demo mode - no database writes
        verbose_logging=False
    )

    print("🔍 Analyzing franchise tag candidates for all 32 NFL teams...")
    print()

    teams_with_candidates = 0
    total_candidates = 0

    # Analyze each team
    for team_id in range(1, 33):
        team = get_team_by_id(team_id)
        team_name = team.full_name if team else f"Team {team_id}"

        # Get franchise tag candidates
        candidates = controller.get_franchise_tag_candidates(team_id)

        if candidates:
            teams_with_candidates += 1
            total_candidates += len(candidates)

            print_separator("-")
            print(f"\n📋 {team_name}")
            print(f"   Found {len(candidates)} franchise tag candidate(s)")

            for i, candidate in enumerate(candidates, 1):
                print_tag_candidate(candidate, i)

    print()
    print_separator()
    print("📊 SUMMARY")
    print_separator()
    print(f"\n   Teams with tag candidates: {teams_with_candidates}/32")
    print(f"   Total tag candidates: {total_candidates}")

    if total_candidates == 0:
        print("\n⚠️  No franchise tag candidates found.")
        print("   This is normal if there are no expiring contracts in the database.")
        print("   To see AI in action:")
        print("   1. Populate database with expiring contracts (Gap 1)")
        print("   2. Add player data with overall ratings (Gap 2)")
        print("   3. Re-run this demo")

    print()
    print_separator()
    print("✅ Demo Complete!")
    print_separator()
    print("\nNext Steps:")
    print("  • Run demo_free_agency_ai.py to see FA simulation")
    print("  • Run demo_roster_cuts_ai.py to see roster management")
    print("  • Run demo_full_ai_offseason.py for end-to-end simulation")
    print()


if __name__ == "__main__":
    main()
