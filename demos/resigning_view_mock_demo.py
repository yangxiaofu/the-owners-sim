#!/usr/bin/env python3
"""
Re-signing View Mock Demo - Fast UI Testing with Hardcoded Data

NO DATABASE REQUIRED - Pure UI testing with mock data.
Perfect for rapid iteration on ResigningView layout, styling, and behavior.

Features:
- Zero database dependency (all data hardcoded)
- Instant startup (~1 second)
- Easy to modify test scenarios
- Multiple test profiles (cap compliant, over cap, star players, etc.)

Usage:
    # Default scenario (cap compliant, mix of players)
    python demos/resigning_view_mock_demo.py

    # Over cap scenario (need restructures)
    python demos/resigning_view_mock_demo.py --scenario over_cap

    # Star players only
    python demos/resigning_view_mock_demo.py --scenario stars

    # Many expiring contracts
    python demos/resigning_view_mock_demo.py --scenario many_players

Available scenarios:
- default: Mix of 8 players, cap compliant
- over_cap: Over cap by $15M, needs cuts/restructures
- stars: Elite players only (QB, WR, EDGE)
- many_players: 15+ expiring contracts
- minimal: Just 2-3 players for simple testing
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, List

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import Qt, QTimer

from game_cycle_ui.views.resigning_view import ResigningView


def create_mock_roster(expiring_player_ids: List[int]) -> List[Dict]:
    """
    Create a full 53-man roster for testing roster cuts.

    Args:
        expiring_player_ids: List of player IDs with expiring contracts

    Returns:
        List of player dicts with player_id, position, overall
    """
    # Generate 53 players across all positions
    roster = []
    player_id = 1000

    # Position distribution (approximate 53-man roster)
    position_counts = {
        "QB": 3, "RB": 4, "FB": 1, "WR": 6, "TE": 3,
        "LT": 2, "LG": 2, "C": 2, "RG": 2, "RT": 2,
        "EDGE": 5, "DT": 4, "MLB": 3, "CB": 5, "SS": 2, "FS": 2,
        "K": 1, "P": 1, "LS": 1
    }

    for position, count in position_counts.items():
        for i in range(count):
            # Starters get higher OVR
            if i == 0:  # Starter
                overall = 75 + (player_id % 18)  # 75-92
            elif i == 1:  # Backup
                overall = 70 + (player_id % 12)  # 70-81
            else:  # Depth
                overall = 65 + (player_id % 10)  # 65-74

            roster.append({
                "player_id": player_id,
                "position": position,
                "overall": overall
            })
            player_id += 1

    return roster


def create_default_scenario() -> tuple[Dict, List[Dict], List[Dict], List[Dict]]:
    """
    Default scenario: Mix of players, cap compliant, WITH RESTRUCTURES.

    Returns:
        Tuple of (cap_data, player_recommendations, restructure_proposals, roster_players)
    """
    cap_data = {
        "available_space": 45_200_000,
        "salary_cap_limit": 255_400_000,
        "total_spending": 210_200_000,
        "dead_money": 0,
        "is_compliant": True,
        "carryover": 5_000_000
    }

    player_recommendations = [
        {
            "player_id": 1,
            "name": "Jalen Hurts",
            "position": "QB",
            "age": 26,
            "overall": 93,
            "gm_recommends": True,
            "proposed_contract": {
                "aav": 51_000_000,
                "years": 5,
                "total": 255_000_000,
                "guaranteed": 180_000_000
            },
            "gm_reasoning": "Elite franchise QB entering prime. Critical to extend before market resets.",
            "priority_tier": 1
        },
        {
            "player_id": 2,
            "name": "A.J. Brown",
            "position": "WR",
            "age": 27,
            "overall": 90,
            "gm_recommends": True,
            "proposed_contract": {
                "aav": 28_000_000,
                "years": 4,
                "total": 112_000_000,
                "guaranteed": 65_000_000
            },
            "gm_reasoning": "Top-5 WR, perfect complement to QB. Excellent value at this price.",
            "priority_tier": 1
        },
        {
            "player_id": 3,
            "name": "Lane Johnson",
            "position": "RT",
            "age": 34,
            "overall": 88,
            "gm_recommends": False,
            "proposed_contract": {
                "aav": 18_000_000,
                "years": 2,
                "total": 36_000_000,
                "guaranteed": 20_000_000
            },
            "gm_reasoning": "Age 34, declining skills. Can draft replacement in Round 2-3.",
            "priority_tier": 5
        },
        {
            "player_id": 4,
            "name": "Haason Reddick",
            "position": "EDGE",
            "age": 30,
            "overall": 85,
            "gm_recommends": True,
            "proposed_contract": {
                "aav": 21_000_000,
                "years": 3,
                "total": 63_000_000,
                "guaranteed": 35_000_000
            },
            "gm_reasoning": "Consistent pass rush production. Team leader. Worth 3-year deal.",
            "priority_tier": 2
        },
        {
            "player_id": 5,
            "name": "Darius Slay",
            "position": "CB",
            "age": 33,
            "overall": 84,
            "gm_recommends": False,
            "proposed_contract": {
                "aav": 14_000_000,
                "years": 2,
                "total": 28_000_000,
                "guaranteed": 12_000_000
            },
            "gm_reasoning": "Aging corner, speed declining. Have promising rookie ready to start.",
            "priority_tier": 4
        },
        {
            "player_id": 6,
            "name": "Fletcher Cox",
            "position": "DT",
            "age": 33,
            "overall": 82,
            "gm_recommends": True,
            "proposed_contract": {
                "aav": 12_000_000,
                "years": 2,
                "total": 24_000_000,
                "guaranteed": 10_000_000
            },
            "gm_reasoning": "Veteran leadership for young D-line. Short deal keeps flexibility.",
            "priority_tier": 3
        },
        {
            "player_id": 7,
            "name": "Dallas Goedert",
            "position": "TE",
            "age": 29,
            "overall": 86,
            "gm_recommends": True,
            "proposed_contract": {
                "aav": 15_000_000,
                "years": 4,
                "total": 60_000_000,
                "guaranteed": 28_000_000
            },
            "gm_reasoning": "Top-10 TE in prime. Key red zone target. Fair market value.",
            "priority_tier": 2
        },
        {
            "player_id": 8,
            "name": "Josh Sweat",
            "position": "EDGE",
            "age": 27,
            "overall": 79,
            "gm_recommends": False,
            "proposed_contract": {
                "aav": 16_000_000,
                "years": 4,
                "total": 64_000_000,
                "guaranteed": 25_000_000
            },
            "gm_reasoning": "Backup-level production asking for starter money. Let him test FA.",
            "priority_tier": 5
        }
    ]

    # Add restructure proposals for testing
    restructure_proposals = [
        {
            "contract_id": 901,
            "player_name": "Brandon Graham",
            "position": "EDGE",
            "overall": 78,
            "current_cap_hit": 13_500_000,
            "new_cap_hit": 8_500_000,
            "cap_savings": 5_000_000,
            "dead_money_added": 10_000_000,
            "gm_reasoning": "Veteran pass rusher. Restructure to create cap flexibility for extensions while keeping him on team.",
            "proposal_id": "restructure_901"
        },
        {
            "contract_id": 902,
            "player_name": "Avonte Maddox",
            "position": "CB",
            "overall": 76,
            "current_cap_hit": 10_000_000,
            "new_cap_hit": 6_500_000,
            "cap_savings": 3_500_000,
            "dead_money_added": 7_000_000,
            "gm_reasoning": "Slot corner on inflated deal. Convert salary to bonus to spread cap hit across future years.",
            "proposal_id": "restructure_902"
        }
    ]

    # Generate full 53-man roster
    expiring_ids = [p["player_id"] for p in player_recommendations]
    roster_players = create_mock_roster(expiring_ids)

    return cap_data, player_recommendations, restructure_proposals, roster_players


def create_over_cap_scenario() -> tuple[Dict, List[Dict], List[Dict], List[Dict]]:
    """
    Over cap scenario: Team needs to shed salary.

    Returns:
        Tuple of (cap_data, player_recommendations, restructure_proposals, roster_players)
    """
    cap_data = {
        "available_space": -15_300_000,  # Over cap!
        "salary_cap_limit": 255_400_000,
        "total_spending": 270_700_000,
        "dead_money": 8_200_000,
        "is_compliant": False,
        "carryover": 0
    }

    player_recommendations = [
        {
            "player_id": 101,
            "name": "Kyler Murray",
            "position": "QB",
            "age": 27,
            "overall": 88,
            "gm_recommends": True,
            "proposed_contract": {
                "aav": 46_000_000,
                "years": 5,
                "total": 230_000_000,
                "guaranteed": 160_000_000
            },
            "gm_reasoning": "Franchise QB. Must extend despite cap issues.",
            "priority_tier": 1
        },
        {
            "player_id": 102,
            "name": "Marquise Brown",
            "position": "WR",
            "age": 27,
            "overall": 81,
            "gm_recommends": False,
            "proposed_contract": {
                "aav": 18_000_000,
                "years": 3,
                "total": 54_000_000,
                "guaranteed": 25_000_000
            },
            "gm_reasoning": "Can't afford WR2 money with cap constraints. Let walk.",
            "priority_tier": 5
        },
        {
            "player_id": 103,
            "name": "Budda Baker",
            "position": "SS",
            "age": 28,
            "overall": 92,
            "gm_recommends": True,
            "proposed_contract": {
                "aav": 19_000_000,
                "years": 4,
                "total": 76_000_000,
                "guaranteed": 42_000_000
            },
            "gm_reasoning": "Elite safety, team captain. Need to find cap space elsewhere.",
            "priority_tier": 1
        }
    ]

    restructure_proposals = [
        {
            "contract_id": 501,
            "player_name": "DeAndre Hopkins",
            "position": "WR",
            "overall": 86,
            "current_cap_hit": 27_500_000,
            "new_cap_hit": 18_500_000,
            "cap_savings": 9_000_000,
            "dead_money_added": 18_000_000,
            "gm_reasoning": "Restructure veteran WR to create immediate cap relief. Pushes cap hit to future years.",
            "proposal_id": "restructure_501"
        },
        {
            "contract_id": 502,
            "player_name": "J.J. Watt",
            "position": "EDGE",
            "overall": 81,
            "current_cap_hit": 23_000_000,
            "new_cap_hit": 16_000_000,
            "cap_savings": 7_000_000,
            "dead_money_added": 14_000_000,
            "gm_reasoning": "Aging pass rusher. Restructure provides short-term relief but increases future dead cap risk.",
            "proposal_id": "restructure_502"
        }
    ]

    # Generate full roster
    expiring_ids = [p["player_id"] for p in player_recommendations]
    roster_players = create_mock_roster(expiring_ids)

    return cap_data, player_recommendations, restructure_proposals, roster_players


def create_stars_scenario() -> tuple[Dict, List[Dict], List[Dict], List[Dict]]:
    """
    Stars scenario: Only elite players (90+ OVR).

    Returns:
        Tuple of (cap_data, player_recommendations, restructure_proposals, roster_players)
    """
    cap_data = {
        "available_space": 62_000_000,
        "salary_cap_limit": 255_400_000,
        "total_spending": 193_400_000,
        "dead_money": 0,
        "is_compliant": True,
        "carryover": 12_000_000
    }

    player_recommendations = [
        {
            "player_id": 201,
            "name": "Patrick Mahomes",
            "position": "QB",
            "age": 29,
            "overall": 99,
            "gm_recommends": True,
            "proposed_contract": {
                "aav": 52_000_000,
                "years": 5,
                "total": 260_000_000,
                "guaranteed": 185_000_000
            },
            "gm_reasoning": "Best QB in the league. Extend at any cost.",
            "priority_tier": 1
        },
        {
            "player_id": 202,
            "name": "Travis Kelce",
            "position": "TE",
            "age": 35,
            "overall": 96,
            "gm_recommends": True,
            "proposed_contract": {
                "aav": 17_000_000,
                "years": 2,
                "total": 34_000_000,
                "guaranteed": 20_000_000
            },
            "gm_reasoning": "Greatest TE ever. Give him 2-year deal to finish career here.",
            "priority_tier": 1
        },
        {
            "player_id": 203,
            "name": "Chris Jones",
            "position": "DT",
            "age": 30,
            "overall": 94,
            "gm_recommends": True,
            "proposed_contract": {
                "aav": 28_000_000,
                "years": 3,
                "total": 84_000_000,
                "guaranteed": 50_000_000
            },
            "gm_reasoning": "Dominant interior pass rusher. Anchor of championship defense.",
            "priority_tier": 1
        },
        {
            "player_id": 204,
            "name": "Nick Bolton",
            "position": "MLB",
            "age": 25,
            "overall": 90,
            "gm_recommends": True,
            "proposed_contract": {
                "aav": 22_000_000,
                "years": 5,
                "total": 110_000_000,
                "guaranteed": 60_000_000
            },
            "gm_reasoning": "Young defensive centerpiece. Lock up for long term.",
            "priority_tier": 1
        }
    ]

    restructure_proposals = []

    # Generate full roster
    expiring_ids = [p["player_id"] for p in player_recommendations]
    roster_players = create_mock_roster(expiring_ids)

    return cap_data, player_recommendations, restructure_proposals, roster_players


def create_many_players_scenario() -> tuple[Dict, List[Dict], List[Dict], List[Dict]]:
    """
    Many players scenario: 15+ expiring contracts.

    Returns:
        Tuple of (cap_data, player_recommendations, restructure_proposals, roster_players)
    """
    cap_data = {
        "available_space": 38_000_000,
        "salary_cap_limit": 255_400_000,
        "total_spending": 217_400_000,
        "dead_money": 3_500_000,
        "is_compliant": True,
        "carryover": 2_000_000
    }

    positions = ["QB", "RB", "WR", "WR", "TE", "LT", "LG", "C", "RG", "RT",
                 "EDGE", "DT", "CB", "CB", "SS", "FS", "K"]
    names = ["Player A", "Player B", "Player C", "Player D", "Player E",
             "Player F", "Player G", "Player H", "Player I", "Player J",
             "Player K", "Player L", "Player M", "Player N", "Player O",
             "Player P", "Player Q"]

    player_recommendations = []
    for i, (pos, name) in enumerate(zip(positions, names), start=1):
        # Vary recommendations
        gm_recommends = (i % 3 != 0)  # Recommend 2 out of every 3
        overall = 75 + (i % 15)  # Vary from 75-89
        aav_base = 15_000_000 if pos == "QB" else 8_000_000
        aav = aav_base + (i % 5) * 1_000_000

        player_recommendations.append({
            "player_id": 300 + i,
            "name": f"{name} ({pos})",
            "position": pos,
            "age": 25 + (i % 8),
            "overall": overall,
            "gm_recommends": gm_recommends,
            "proposed_contract": {
                "aav": aav,
                "years": 3 + (i % 2),
                "total": aav * (3 + (i % 2)),
                "guaranteed": int(aav * (3 + (i % 2)) * 0.5)
            },
            "gm_reasoning": f"{'Recommend extension' if gm_recommends else 'Let walk'} - {pos} depth",
            "priority_tier": (i % 5) + 1
        })

    restructure_proposals = []

    # Generate full roster
    expiring_ids = [p["player_id"] for p in player_recommendations]
    roster_players = create_mock_roster(expiring_ids)

    return cap_data, player_recommendations, restructure_proposals, roster_players


def create_minimal_scenario() -> tuple[Dict, List[Dict], List[Dict], List[Dict]]:
    """
    Minimal scenario: Just 2-3 players for simple UI testing.

    Returns:
        Tuple of (cap_data, player_recommendations, restructure_proposals, roster_players)
    """
    cap_data = {
        "available_space": 50_000_000,
        "salary_cap_limit": 255_400_000,
        "total_spending": 205_400_000,
        "dead_money": 0,
        "is_compliant": True,
        "carryover": 0
    }

    player_recommendations = [
        {
            "player_id": 401,
            "name": "Test QB",
            "position": "QB",
            "age": 28,
            "overall": 85,
            "gm_recommends": True,
            "proposed_contract": {
                "aav": 35_000_000,
                "years": 4,
                "total": 140_000_000,
                "guaranteed": 90_000_000
            },
            "gm_reasoning": "Solid starter, extend for continuity.",
            "priority_tier": 1
        },
        {
            "player_id": 402,
            "name": "Test WR",
            "position": "WR",
            "age": 26,
            "overall": 82,
            "gm_recommends": False,
            "proposed_contract": {
                "aav": 18_000_000,
                "years": 3,
                "total": 54_000_000,
                "guaranteed": 25_000_000
            },
            "gm_reasoning": "Inconsistent production, can replace in draft.",
            "priority_tier": 4
        }
    ]

    restructure_proposals = []

    # Generate full roster
    expiring_ids = [p["player_id"] for p in player_recommendations]
    roster_players = create_mock_roster(expiring_ids)

    return cap_data, player_recommendations, restructure_proposals, roster_players


def get_scenario_data(scenario_name: str) -> tuple[Dict, List[Dict], List[Dict], List[Dict]]:
    """
    Get mock data for specified scenario.

    Args:
        scenario_name: Name of scenario (default, over_cap, stars, many_players, minimal)

    Returns:
        Tuple of (cap_data, player_recommendations, restructure_proposals, roster_players)
    """
    scenarios = {
        "default": create_default_scenario,
        "over_cap": create_over_cap_scenario,
        "stars": create_stars_scenario,
        "many_players": create_many_players_scenario,
        "minimal": create_minimal_scenario
    }

    scenario_func = scenarios.get(scenario_name, create_default_scenario)
    return scenario_func()


# ============================================================================
# Signal Handlers for Mock Demonstration
# ============================================================================

def create_restructure_handlers(view, cap_data: Dict):
    """
    Create and return signal handlers for restructure proposals.

    With the new dialog-based flow, these handlers simulate the backend
    response when a restructure is approved or rejected via the dialog.

    Args:
        view: ResigningView instance
        cap_data: Dict with cap data (will be updated as restructures complete)

    Returns:
        Tuple of (on_approved, on_rejected) handler functions
    """
    # Track approved savings for cap updates
    total_savings = {"amount": 0}

    def on_restructure_approved(proposal: Dict):
        """Handle restructure approval from dialog."""
        contract_id = proposal.get("contract_id")
        cap_savings = proposal.get("cap_savings", 0)
        player_name = proposal.get("player_name", "Unknown")

        print(f"[MOCK] Restructure APPROVED for {player_name} (contract {contract_id})")
        print(f"[MOCK] Cap savings: ${cap_savings:,}")

        # Track total savings
        total_savings["amount"] += cap_savings

        # Update cap data
        cap_data["available_space"] += cap_savings
        cap_data["total_spending"] -= cap_savings

        # Refresh cap display
        print(f"[MOCK] Refreshing cap display (total savings: ${total_savings['amount']:,})")
        view.set_cap_data(cap_data)

    def on_restructure_rejected(proposal: Dict):
        """Handle restructure rejection from dialog."""
        contract_id = proposal.get("contract_id")
        player_name = proposal.get("player_name", "Unknown")
        print(f"[MOCK] Restructure REJECTED for {player_name} (contract {contract_id})")

    return on_restructure_approved, on_restructure_rejected


def create_reevaluation_handler(view, scenario_name: str):
    """
    Create handler that simulates GM re-evaluation using scenario function.

    Reuses the existing get_scenario_data() API to regenerate recommendations,
    simulating what would happen when the GM re-evaluates based on current cap.

    Args:
        view: ResigningView instance
        scenario_name: Name of scenario to regenerate (e.g., "default", "over_cap")

    Returns:
        Handler function for gm_reevaluation_requested signal
    """
    def on_reevaluation_requested():
        """Simulate GM re-evaluation - regenerate using scenario function."""
        print()
        print("[MOCK] Re-evaluating GM recommendations with current cap...")

        # Simulate backend processing delay (1 second)
        QTimer.singleShot(1000, lambda: complete_reevaluation())

    def complete_reevaluation():
        """Complete re-evaluation by calling scenario function again."""
        # Call the scenario function to get fresh recommendations
        # This simulates GM re-generating based on current cap
        _, new_recommendations, _, _ = get_scenario_data(scenario_name)

        print(f"[MOCK] Re-evaluation complete - recommendations regenerated")

        # Call view with is_reevaluation=True to trigger animations
        view.set_all_players(new_recommendations, is_reevaluation=True)

    return on_reevaluation_requested


def main():
    """Main entry point for re-signing view mock demo."""
    parser = argparse.ArgumentParser(
        description="Re-signing View Mock Demo - Fast UI testing with hardcoded data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Scenarios:
    default       - Mix of 8 players, cap compliant (default)
    over_cap      - Over cap by $15M, needs restructures
    stars         - Elite players only (90+ OVR)
    many_players  - 15+ expiring contracts
    minimal       - Just 2-3 players for simple testing

Examples:
    # Default scenario
    python demos/resigning_view_mock_demo.py

    # Over cap scenario
    python demos/resigning_view_mock_demo.py --scenario over_cap

    # Many players
    python demos/resigning_view_mock_demo.py --scenario many_players
        """
    )
    parser.add_argument(
        '--scenario',
        default='default',
        choices=['default', 'over_cap', 'stars', 'many_players', 'minimal'],
        help='Test scenario to load (default: default)'
    )
    args = parser.parse_args()

    print("=" * 70)
    print("RE-SIGNING VIEW MOCK DEMO - Fast UI Testing (No Database)")
    print("=" * 70)
    print()
    print(f"Scenario: {args.scenario}")
    print()

    # Get mock data for scenario
    cap_data, player_recommendations, restructure_proposals, roster_players = get_scenario_data(args.scenario)

    print(f"Mock Data Generated:")
    print(f"  Cap Space: ${cap_data['available_space']:,}")
    print(f"  Expiring Contracts: {len(player_recommendations)}")
    print(f"  GM Recommends Extend: {sum(1 for p in player_recommendations if p['gm_recommends'])}")
    print(f"  GM Recommends Release: {sum(1 for p in player_recommendations if not p['gm_recommends'])}")
    print(f"  Restructure Proposals: {len(restructure_proposals)}")
    print(f"  Full Roster: {len(roster_players)} players")
    print()

    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Create main window
    window = QMainWindow()
    window.setWindowTitle(f"Re-signing View Mock Demo - {args.scenario.replace('_', ' ').title()}")
    window.resize(1600, 1000)

    # Create view
    view = ResigningView()

    # Set context (mock values - DB path won't be used)
    view.set_context(
        dynasty_id="mock_dynasty",
        db_path=":memory:",  # In-memory DB (won't actually be used)
        season=2025,
        team_name="Mock Team",
        team_id=1
    )

    # Connect signal handlers for restructure proposals
    on_approved, on_rejected = create_restructure_handlers(view, cap_data)
    view.restructure_proposal_approved.connect(on_approved)
    view.restructure_proposal_rejected.connect(on_rejected)

    # Connect signal handler for GM re-evaluation
    reevaluation_handler = create_reevaluation_handler(view, args.scenario)
    view.gm_reevaluation_requested.connect(reevaluation_handler)

    # Disable early cuts button (requires database)
    # Override the button click handler to show a message instead
    def show_early_cuts_message():
        print()
        print("=" * 70)
        print("[DEMO LIMITATION] Early Roster Cuts")
        print("=" * 70)
        print("The Early Roster Cuts feature requires database access and cannot")
        print("be demonstrated in this mock demo.")
        print()
        print("In the real application (main2.py), this button would:")
        print("  • Load GM-recommended roster cuts from the database")
        print("  • Show cut proposals with cap savings and GM reasoning")
        print("  • Allow approval/rejection of individual cuts")
        print("  • Update roster and cap space after cuts are approved")
        print("=" * 70)
        print()

    view.early_cuts_btn.clicked.disconnect()
    view.early_cuts_btn.clicked.connect(show_early_cuts_message)

    # Load mock data
    view.set_cap_data(cap_data)
    view.set_all_players(player_recommendations)

    if restructure_proposals:
        view.set_restructure_proposals(restructure_proposals)

    # Set roster health for position group display and early cuts
    expiring_ids = {p["player_id"] for p in player_recommendations}
    view.set_roster_health(roster_players, expiring_ids)

    window.setCentralWidget(view)
    window.show()

    print("✅ ResigningView launched with mock data!")
    print()
    print("Features:")
    print("  • Toggle approve/reject for each player")
    print("  • See real-time cap projections")
    print("  • View GM reasoning (hover over player names)")
    print("  • Restructure Contracts dialog ← TOGGLE PATTERN!")
    print("    - Click 'Restructure Contracts...' button to open dialog")
    print("    - All proposals pre-approved (toggle ON by default)")
    print("    - Toggle OFF to reject individual restructures")
    print("    - Rejected rows dim to show status")
    print("    - 'Select All' toggles all back to ON")
    print("    - Summary shows 'X restructures selected (+$Y.YM savings)'")
    print("    - Confirm to execute all selections")
    print("  • Re-evaluate GM recommendations ← FULLY FUNCTIONAL!")
    print("    - Click '⟳ Re-evaluate GM' button")
    print("    - Confirm to regenerate recommendations")
    print("    - See success message and green row animations")
    print("  • Early cuts button (shows demo limitation message)")
    print()
    print("UX Consistency:")
    print("  Extension recommendations use toggle pattern for approve/reject.")
    print("  Restructure dialog now matches with toggle switches (ON=approved).")
    print()
    print("Note: Changes are simulated (no database persistence)")
    print()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
