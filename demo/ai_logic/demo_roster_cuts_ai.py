"""
Roster Cut AI Demo

Demonstrates Gap 7: AI cutting 90-man rosters down to 53 players.
Shows how AI ranks players by value and meets NFL position minimums.

Run: PYTHONPATH=src python demo/ai_logic/demo_roster_cuts_ai.py
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from offseason.roster_manager import RosterManager
from team_management.teams.team_loader import get_team_by_id


def print_separator(char="=", length=80):
    """Print a visual separator."""
    print(char * length)


def create_mock_90_man_roster():
    """Create a mock 90-man roster for testing."""
    positions = [
        # QBs (3)
        ('quarterback', [85, 70, 65]),
        # RBs (6)
        ('running_back', [82, 78, 72, 68, 65, 62]),
        # WRs (10)
        ('wide_receiver', [88, 84, 80, 76, 72, 70, 68, 66, 64, 62]),
        # TEs (4)
        ('tight_end', [80, 75, 70, 65]),
        # OL (12)
        ('left_tackle', [86, 72, 68]),
        ('left_guard', [80, 70, 66]),
        ('center', [82, 74, 68]),
        ('right_guard', [78, 72, 65]),
        ('right_tackle', [84, 70, 66]),
        # DL (12)
        ('defensive_end', [87, 82, 76, 72, 68, 64]),
        ('defensive_tackle', [85, 80, 74, 70, 66, 62]),
        # LBs (10)
        ('linebacker', [86, 82, 78, 74, 72, 70, 68, 66, 64, 62]),
        # DBs (14)
        ('cornerback', [88, 84, 80, 76, 72, 70, 68, 66]),
        ('safety', [85, 82, 78, 74, 70, 68]),
        # Special Teams (2)
        ('kicker', [78]),
        ('punter', [76])
    ]

    roster = []
    player_id = 2000

    for position, overalls in positions:
        for overall in overalls:
            # Mock cap hit (varies by position and overall)
            base_cap = 1_000_000  # League minimum
            if overall >= 85:
                cap_hit = base_cap * 15  # $15M for elite
            elif overall >= 80:
                cap_hit = base_cap * 8   # $8M for starters
            elif overall >= 70:
                cap_hit = base_cap * 3   # $3M for backups
            else:
                cap_hit = base_cap       # Min for depth

            roster.append({
                'player_id': player_id,
                'player_name': f"{position[:2].upper()}{player_id}",
                'position': position,
                'overall': overall,
                'cap_hit': cap_hit
            })
            player_id += 1

    return roster


def print_roster_summary(roster, title):
    """Print a summary of a roster."""
    print(f"\n{title}")
    print(f"Total Players: {len(roster)}")

    # Count by position
    position_counts = {}
    for player in roster:
        pos = player['position']
        position_counts[pos] = position_counts.get(pos, 0) + 1

    print("\nPosition Breakdown:")
    for pos in sorted(position_counts.keys()):
        print(f"  {pos.replace('_', ' ').title()}: {position_counts[pos]}")


def main():
    """Run roster cut AI demo."""
    print_separator()
    print("✂️  ROSTER CUT AI DEMONSTRATION")
    print_separator()
    print("\nThis demo shows AI cutting 90-man rosters down to 53 players.")
    print("\nAI Ranking Algorithm:")
    print("  • Value Score = (Position Value × Overall) - Cap Hit Penalty")
    print("  • Premium positions (QB, DE, OT) get higher multipliers")
    print("  • Expensive players get penalized in value score")
    print("  • NFL position minimums enforced (QB≥1, OL≥5, DL≥4, etc.)")
    print()

    # Initialize manager
    roster_manager = RosterManager(
        database_path="data/database/nfl_simulation.db",
        dynasty_id="phase2_testing",
        season_year=2025,
        enable_persistence=False
    )

    # Create mock 90-man roster
    print("📝 Creating mock 90-man roster...")
    roster_90 = create_mock_90_man_roster()
    print(f"   Created {len(roster_90)} players")
    print()

    # Monkey-patch the mock roster into the manager for demo
    roster_manager._get_mock_90_man_roster = lambda team_id: roster_90

    # Run AI roster cuts for a sample team
    team_id = 22  # Detroit Lions
    team = get_team_by_id(team_id)
    team_name = team.full_name if team else f"Team {team_id}"

    print(f"🏈 Running roster cuts for {team_name}...")
    print()

    result = roster_manager.finalize_53_man_roster_ai(team_id)

    # Display results
    print_separator("-")
    print_roster_summary(result['final_roster'], "✅ FINAL 53-MAN ROSTER")
    print()
    print_separator("-")
    print_roster_summary(result['cuts'], "❌ PLAYERS CUT")

    # Show top 10 players kept (by value score)
    print()
    print_separator("-")
    print("\n⭐ TOP 10 PLAYERS KEPT (by Value Score)")
    final_roster_sorted = sorted(result['final_roster'], key=lambda p: p.get('value_score', 0), reverse=True)

    for i, player in enumerate(final_roster_sorted[:10], 1):
        print(f"\n   #{i}. {player['player_name']}")
        print(f"       Position: {player['position'].replace('_', ' ').title()}")
        print(f"       Overall: {player['overall']} OVR")
        print(f"       Cap Hit: ${player['cap_hit']:,}")
        print(f"       Value Score: {player.get('value_score', 0):.2f}")

    # Show bottom 5 players cut (lowest value score)
    print()
    print_separator("-")
    print("\n🗑️  BOTTOM 5 PLAYERS CUT (lowest Value Score)")
    cuts_sorted = sorted(result['cuts'], key=lambda p: p.get('value_score', 0))

    for i, player in enumerate(cuts_sorted[:5], 1):
        print(f"\n   #{i}. {player['player_name']}")
        print(f"       Position: {player['position'].replace('_', ' ').title()}")
        print(f"       Overall: {player['overall']} OVR")
        print(f"       Cap Hit: ${player['cap_hit']:,}")
        print(f"       Value Score: {player.get('value_score', 0):.2f}")

    # Validate position minimums
    print()
    print_separator("-")
    print("\n✓ NFL POSITION MINIMUM VALIDATION")

    # Count positions in final roster
    ol_positions = {'left_tackle', 'right_tackle', 'left_guard', 'right_guard', 'center'}
    dl_positions = {'defensive_end', 'defensive_tackle'}
    db_positions = {'cornerback', 'safety'}

    position_counts = {
        'QB': 0,
        'OL': 0,
        'DL': 0,
        'LB': 0,
        'DB': 0,
        'K': 0,
        'P': 0
    }

    for player in result['final_roster']:
        pos = player['position']
        if pos == 'quarterback':
            position_counts['QB'] += 1
        elif pos in ol_positions:
            position_counts['OL'] += 1
        elif pos in dl_positions:
            position_counts['DL'] += 1
        elif pos == 'linebacker':
            position_counts['LB'] += 1
        elif pos in db_positions:
            position_counts['DB'] += 1
        elif pos == 'kicker':
            position_counts['K'] += 1
        elif pos == 'punter':
            position_counts['P'] += 1

    minimums = {'QB': 1, 'OL': 5, 'DL': 4, 'LB': 3, 'DB': 3, 'K': 1, 'P': 1}

    for pos_group, count in position_counts.items():
        minimum = minimums[pos_group]
        status = "✓" if count >= minimum else "✗"
        print(f"   {status} {pos_group}: {count}/{minimum} (minimum)")

    print()
    print_separator()
    print("📊 SUMMARY")
    print_separator()
    print(f"\n   Roster Size: {len(result['final_roster'])}/53")
    print(f"   Players Cut: {result['total_cut']}")
    print(f"   Position Minimums: {'All met ✓' if all(position_counts[k] >= minimums[k] for k in minimums) else 'FAILED ✗'}")

    print()
    print_separator()
    print("✅ Demo Complete!")
    print_separator()
    print("\nNext Steps:")
    print("  • Run demo_full_ai_offseason.py for complete offseason simulation")
    print("  • Integrate with real database for production use")
    print()


if __name__ == "__main__":
    main()
