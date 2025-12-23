#!/usr/bin/env python3
"""
Trade Quick Test - Fast iteration for trade proposal testing.

Tests a single team's trade proposal generation in ~5 seconds.
Much faster than running full trade_diagnosis_demo.py (~2 minutes).

Usage:
    PYTHONPATH=src python demos/trade_quick_test.py
    PYTHONPATH=src python demos/trade_quick_test.py --team 15 --philosophy win_now
    PYTHONPATH=src python demos/trade_quick_test.py --team 21 --philosophy rebuild
"""

import sys
import time
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from game_cycle.models.owner_directives import OwnerDirectives
from game_cycle.services.proposal_generators.trade_generator import TradeProposalGenerator
from game_cycle.services.trade_service import TradeService
from game_cycle_ui.controllers.dynasty_controller import GameCycleDynastyController
import sqlite3
import json


def get_team_name(team_id: int) -> str:
    """Get team name from teams.json."""
    teams_file = project_root / "src" / "data" / "teams.json"
    try:
        with open(teams_file) as f:
            data = json.load(f)
            team = data.get("teams", {}).get(str(team_id), {})
            return team.get("full_name", f"Team {team_id}")
    except:
        return f"Team {team_id}"


def get_dynasty_info(db_path: str) -> tuple:
    """Get dynasty_id and season from database."""
    gc_controller = GameCycleDynastyController(db_path)
    dynasties = gc_controller.list_dynasties()
    if not dynasties:
        return None, None

    dynasty_id = dynasties[0]['dynasty_id']

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(season) FROM dynasty_state WHERE dynasty_id = ?", (dynasty_id,))
    row = cursor.fetchone()
    conn.close()

    season = row[0] if row and row[0] else 2026
    return dynasty_id, season


def find_expendable_players(db_path: str, dynasty_id: str, season: int, team_id: int) -> List[int]:
    """Find some expendable players for testing."""
    trade_service = TradeService(db_path, dynasty_id, season)
    players = trade_service.get_tradeable_players(team_id)

    # For rebuild: veterans with high cap
    # For win_now: low-value depth players
    expendable = []
    for p in players:
        age = p.get("age", 0)
        ovr = p.get("overall", 70)
        cap = p.get("cap_hit", 0)

        # Expendable: older or lower-rated players
        if age >= 30 or ovr < 78:
            expendable.append(p["player_id"])
            if len(expendable) >= 3:
                break

    return expendable


def run_test(team_id: int, philosophy: str, db_path: str):
    """Run trade proposal test for a single team."""
    print(f"\n{'='*60}")
    print(f"TRADE QUICK TEST")
    print(f"{'='*60}")

    dynasty_id, season = get_dynasty_info(db_path)
    if not dynasty_id:
        print("ERROR: No dynasty found in database")
        return

    print(f"Dynasty: {dynasty_id}")
    print(f"Season: {season}")
    print(f"Team: {get_team_name(team_id)} (#{team_id})")
    print(f"Philosophy: {philosophy}")
    print()

    # Get expendable players
    expendable_ids = find_expendable_players(db_path, dynasty_id, season, team_id)
    print(f"Expendable players: {len(expendable_ids)} found")

    # Create directives
    directives = OwnerDirectives(
        dynasty_id=dynasty_id,
        team_id=team_id,
        season=season,
        team_philosophy=philosophy,
        budget_stance="moderate",
        priority_positions=["EDGE", "CB", "WR"] if philosophy == "win_now" else [],
        protected_player_ids=[],
        expendable_player_ids=expendable_ids,
    )

    # Generate proposals with timing
    print(f"\nGenerating proposals...")
    start = time.time()

    generator = TradeProposalGenerator(
        db_path=db_path,
        dynasty_id=dynasty_id,
        season=season,
        team_id=team_id,
        directives=directives,
    )
    proposals = generator.generate_proposals()

    elapsed = time.time() - start
    print(f"Generated {len(proposals)} proposals in {elapsed:.2f}s")

    # Display proposals
    print(f"\n{'-'*60}")
    if not proposals:
        print("No trade proposals generated.")
        print("\nDEBUG INFO:")
        print(f"  - Philosophy: {philosophy}")
        print(f"  - Expendable IDs: {expendable_ids}")
        print(f"  - Priority positions: {directives.priority_positions}")
    else:
        # Track unique partners
        partners = set()

        for i, p in enumerate(proposals, 1):
            details = p.details or {}
            partner = details.get("trade_partner", "Unknown")
            partners.add(partner)

            print(f"\n[{i}] Trade with {partner}")
            print(f"    Priority: {p.priority} | Confidence: {p.confidence:.0%}")

            # Show what we send
            sending = details.get("sending", [])
            if sending:
                print("    WE SEND:")
                for asset in sending:
                    if asset.get("type") == "player":
                        print(f"      - {asset.get('name')} ({asset.get('position')}, {asset.get('overall')} OVR)")
                    else:
                        print(f"      - {asset.get('name')}")

            # Show what we receive
            receiving = details.get("receiving", [])
            if receiving:
                print("    WE RECEIVE:")
                for asset in receiving:
                    if asset.get("type") == "player":
                        print(f"      - {asset.get('name')} ({asset.get('position')}, {asset.get('overall')} OVR)")
                    else:
                        print(f"      - {asset.get('name')}")

            # Value
            value = details.get("value_differential", 0)
            value_str = f"+${value:,}" if value >= 0 else f"-${abs(value):,}"
            print(f"    Value: {value_str}")

        # Summary
        print(f"\n{'-'*60}")
        print(f"SUMMARY:")
        print(f"  - Total proposals: {len(proposals)}")
        print(f"  - Unique trade partners: {len(partners)}")
        print(f"  - Partners: {', '.join(sorted(partners))}")

    print(f"\n{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Quick trade proposal test")
    parser.add_argument("--team", type=int, default=15, help="Team ID (1-32)")
    parser.add_argument("--philosophy", choices=["win_now", "rebuild", "maintain"],
                        default="win_now", help="Team philosophy")
    parser.add_argument("--db", type=str, default=None, help="Database path")
    args = parser.parse_args()

    # Use snapshot database by default
    if args.db:
        db_path = args.db
    else:
        db_path = str(project_root / "demos" / "snapshots" / "trade_diagnosis.db")

    if not Path(db_path).exists():
        print(f"ERROR: Database not found: {db_path}")
        print("Run trade_diagnosis_demo.py first to create snapshot.")
        return 1

    run_test(args.team, args.philosophy, db_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
