"""
Free Agency AI Demo

Demonstrates Gap 5: AI simulating 30 days of NFL free agency.
Shows how AI teams sign free agents based on positional needs and market value.

Run: PYTHONPATH=src python demo/ai_logic/demo_free_agency_ai.py
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from offseason.free_agency_manager import FreeAgencyManager
from offseason.team_needs_analyzer import TeamNeedsAnalyzer
from offseason.market_value_calculator import MarketValueCalculator
from team_management.teams.team_loader import get_team_by_id


def print_separator(char="=", length=80):
    """Print a visual separator."""
    print(char * length)


def create_mock_fa_pool():
    """Create a mock free agent pool for testing."""
    positions = ['quarterback', 'running_back', 'wide_receiver', 'tight_end',
                 'left_tackle', 'defensive_end', 'linebacker', 'cornerback', 'safety']

    mock_fas = []
    player_id = 1000

    # Create 100 mock free agents with varying ratings
    for i in range(100):
        position = positions[i % len(positions)]
        base_overall = 90 - (i // 10) * 5  # 90, 85, 80, 75, 70, 65, 60, 55, 50, 45

        mock_fas.append({
            'player_id': player_id + i,
            'player_name': f"FA {position[:2].upper()}{i+1}",
            'position': position,
            'overall': base_overall,
            'age': 25 + (i % 8),
            'years_pro': 3 + (i % 6)
        })

    return mock_fas


def main():
    """Run free agency AI simulation demo."""
    print_separator()
    print("💰 FREE AGENCY AI SIMULATION DEMO")
    print_separator()
    print("\nThis demo simulates 30 days of NFL free agency with AI teams making signings.")
    print("\nFA Period Tiers:")
    print("  • Days 1-3 (Legal Tampering): Elite FAs (85+ OVR), max 2 signings/team")
    print("  • Days 4-14: Starters (75+ OVR), max 3 signings/team")
    print("  • Days 15-30: Depth pieces (65+ OVR), max 5 signings/team")
    print()

    # Initialize manager
    fa_manager = FreeAgencyManager(
        database_path="data/database/nfl_simulation.db",
        dynasty_id="phase2_testing",
        season_year=2025,
        enable_persistence=False,
        verbose_logging=True
    )

    # Create mock FA pool
    available_fas = create_mock_fa_pool()
    print(f"📝 Created mock free agent pool: {len(available_fas)} players")
    print()

    # User team (won't make signings)
    user_team_id = 7  # Pittsburgh

    # Simulate 30 days of free agency
    all_signings = []
    days_to_show = [1, 2, 3, 7, 14, 21, 30]  # Only show selected days for brevity

    print("🏈 SIMULATING FREE AGENCY...")
    print()

    for day in range(1, 31):
        # Simulate this day
        day_signings = fa_manager.simulate_free_agency_day(
            day_number=day,
            user_team_id=user_team_id,
            available_fas=available_fas
        )

        all_signings.extend(day_signings)

        # Remove signed players from pool
        signed_ids = {s['player_id'] for s in day_signings}
        available_fas = [fa for fa in available_fas if fa['player_id'] not in signed_ids]

        # Show details for selected days
        if day in days_to_show:
            print_separator("-")
            print(f"\n📅 DAY {day} RESULTS")

            if day_signings:
                print(f"   Signings: {len(day_signings)}")
                print(f"   FAs Remaining: {len(available_fas)}")
                print("\n   Notable Signings:")

                # Show top 5 signings by overall
                top_signings = sorted(day_signings, key=lambda x: x['overall'], reverse=True)[:5]

                for signing in top_signings:
                    team = get_team_by_id(signing['team_id'])
                    team_name = team.full_name if team else f"Team {signing['team_id']}"
                    print(f"      • {signing['player_name']} ({signing['overall']} OVR {signing['position']}) → {team_name}")
                    print(f"        ${signing['contract_aav']:.2f}M/year for {signing['contract_years']} years")
            else:
                print("   No signings today")
                print(f"   FAs Remaining: {len(available_fas)}")

    # Final summary
    print()
    print_separator()
    print("📊 30-DAY FREE AGENCY SUMMARY")
    print_separator()

    print(f"\n   Total Signings: {len(all_signings)}")
    print(f"   FAs Remaining: {len(available_fas)}")

    # Signings by tier
    elite_signings = [s for s in all_signings if s['overall'] >= 85]
    starter_signings = [s for s in all_signings if 75 <= s['overall'] < 85]
    depth_signings = [s for s in all_signings if s['overall'] < 75]

    print(f"\n   Elite Signings (85+ OVR): {len(elite_signings)}")
    print(f"   Starter Signings (75-84 OVR): {len(starter_signings)}")
    print(f"   Depth Signings (<75 OVR): {len(depth_signings)}")

    # Top contracts
    print("\n   💸 Top 5 Contracts:")
    top_contracts = sorted(all_signings, key=lambda x: x['contract_aav'], reverse=True)[:5]
    for i, signing in enumerate(top_contracts, 1):
        team = get_team_by_id(signing['team_id'])
        team_name = team.full_name if team else f"Team {signing['team_id']}"
        print(f"      #{i}. {signing['player_name']} ({signing['overall']} OVR {signing['position']})")
        print(f"          ${signing['contract_aav']:.2f}M/year × {signing['contract_years']} years → {team_name}")

    # Position breakdown
    position_signings = {}
    for signing in all_signings:
        pos = signing['position']
        position_signings[pos] = position_signings.get(pos, 0) + 1

    print("\n   📍 Signings by Position:")
    for pos, count in sorted(position_signings.items(), key=lambda x: x[1], reverse=True):
        print(f"      {pos.replace('_', ' ').title()}: {count}")

    print()
    print_separator()
    print("✅ Demo Complete!")
    print_separator()
    print("\nNext Steps:")
    print("  • Run demo_roster_cuts_ai.py to see roster management")
    print("  • Run demo_full_ai_offseason.py for end-to-end simulation")
    print()


if __name__ == "__main__":
    main()
