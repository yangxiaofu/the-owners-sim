#!/usr/bin/env python3
"""
Trade Diagnosis Demo - Analyze GM Trade Proposals by Archetype.

This demo generates and displays trade proposals for different teams based on
their GM archetypes. Useful for benchmarking simulated trades against real-life
NFL trades.

Usage:
    PYTHONPATH=src python demos/trade_diagnosis_demo.py --dynasty testd272ffd3
    PYTHONPATH=src python demos/trade_diagnosis_demo.py --archetype win_now
    PYTHONPATH=src python demos/trade_diagnosis_demo.py --team 15 6 30
"""

import sys
import shutil
import argparse
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from game_cycle.database.connection import GameCycleDatabase
from game_cycle.models.owner_directives import OwnerDirectives
from game_cycle.services.proposal_generators.trade_generator import TradeProposalGenerator
from game_cycle.services.trade_service import TradeService
from game_cycle_ui.controllers.dynasty_controller import GameCycleDynastyController
from team_management.gm_archetype import GMArchetype
from team_management.gm_archetype_factory import GMArchetypeFactory


# Load team data once at module level
_TEAM_DATA: Dict[int, Dict] = {}


def _load_team_data():
    """Load team data from teams.json."""
    global _TEAM_DATA
    if _TEAM_DATA:
        return
    teams_file = project_root / "src" / "data" / "teams.json"
    try:
        with open(teams_file) as f:
            data = json.load(f)
            for tid, team in data.get("teams", {}).items():
                _TEAM_DATA[int(tid)] = team
    except Exception:
        pass


def get_team_name(team_id: int) -> str:
    """Get team full name from ID."""
    _load_team_data()
    team = _TEAM_DATA.get(team_id, {})
    return team.get("full_name", f"Team {team_id}")


def get_team_abbrev(team_id: int) -> str:
    """Get team abbreviation from ID."""
    _load_team_data()
    team = _TEAM_DATA.get(team_id, {})
    return team.get("abbreviation", f"T{team_id}")


def create_snapshot(source_db: Path, snapshot_db: Path, force: bool = False) -> bool:
    """Create database snapshot if needed."""
    if not source_db.exists():
        print(f"ERROR: Source database not found: {source_db}")
        return False

    if force or not snapshot_db.exists():
        print(f"Creating snapshot from {source_db}...")
        snapshot_db.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_db, snapshot_db)
        # Copy WAL/SHM files if they exist
        for ext in ['-wal', '-shm']:
            wal_source = source_db.with_suffix(source_db.suffix + ext)
            if wal_source.exists():
                shutil.copy2(wal_source, snapshot_db.with_suffix(snapshot_db.suffix + ext))
        print(f"Snapshot created: {snapshot_db}")
    else:
        print(f"Using existing snapshot: {snapshot_db}")
    return True


def get_dynasty_info(db_path: str, target_dynasty_id: Optional[str] = None) -> Tuple[Optional[str], Optional[int]]:
    """Get dynasty_id and season from database."""
    import sqlite3

    gc_controller = GameCycleDynastyController(db_path)
    dynasties = gc_controller.list_dynasties()

    if not dynasties:
        return None, None

    # Find matching dynasty or use first
    dynasty_id = None
    if target_dynasty_id:
        for d in dynasties:
            if d['dynasty_id'].lower() == target_dynasty_id.lower():
                dynasty_id = d['dynasty_id']
                break
        if not dynasty_id:
            print(f"Warning: Dynasty '{target_dynasty_id}' not found, using first dynasty")

    if not dynasty_id:
        dynasty_id = dynasties[0]['dynasty_id']

    # Query the ACTUAL current season from dynasty_state
    # (list_dynasties doesn't return current_season)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT MAX(season) FROM dynasty_state WHERE dynasty_id = ?
    """, (dynasty_id,))
    row = cursor.fetchone()
    conn.close()

    season = row[0] if row and row[0] else 2025
    return dynasty_id, season


def map_archetype_to_philosophy(archetype: GMArchetype) -> str:
    """Map GM archetype to owner directive philosophy."""
    if archetype.win_now_mentality >= 0.7:
        return "win_now"
    elif archetype.win_now_mentality <= 0.4 and archetype.draft_pick_value >= 0.7:
        return "rebuild"
    return "maintain"


def map_archetype_to_budget(archetype: GMArchetype) -> str:
    """Map GM archetype to budget stance."""
    if archetype.cap_management >= 0.7:
        return "conservative"
    elif archetype.cap_management <= 0.35:
        return "aggressive"
    return "moderate"


def find_expendable_players(
    db_path: str,
    dynasty_id: str,
    season: int,
    team_id: int,
    archetype: GMArchetype
) -> List[int]:
    """Find expendable players based on archetype traits."""
    try:
        trade_service = TradeService(db_path, dynasty_id, season)
        players = trade_service.get_tradeable_players(team_id)

        expendable = []
        for p in players:
            player_id = p.get("player_id")
            age = p.get("age", 25)
            overall = p.get("overall_rating", 70)
            cap_hit = p.get("cap_hit", 0)

            # Rebuilder: Veterans 28+ with high salary are expendable
            if archetype.win_now_mentality <= 0.4:
                if age >= 28 and cap_hit >= 5_000_000:
                    expendable.append(player_id)
            # Win-Now: Low performers are expendable
            elif archetype.win_now_mentality >= 0.7:
                if overall < 75 and age < 26:
                    expendable.append(player_id)
            # Balanced: Low performers at any age
            else:
                if overall < 72:
                    expendable.append(player_id)

            # Limit to 10
            if len(expendable) >= 10:
                break

        return expendable
    except Exception as e:
        print(f"    [WARN] Could not find expendable players: {e}")
        return []


def find_priority_positions(archetype: GMArchetype) -> List[str]:
    """Determine priority positions based on archetype.

    v1.2: Win-Now teams always return default premium positions to ensure
    acquisition proposals are generated (matches trade_generator.py logic).
    """
    # Default premium positions for Win-Now (v1.2 - trade realism)
    DEFAULT_WIN_NOW_POSITIONS = ["EDGE", "CB", "WR", "OT", "DT"]

    if archetype.win_now_mentality >= 0.7:
        # Win-Now: Always return premium positions
        if archetype.premium_position_focus >= 0.6:
            return ["QB", "EDGE", "LT", "WR", "CB"]
        return DEFAULT_WIN_NOW_POSITIONS
    elif archetype.win_now_mentality <= 0.4:
        # Rebuilder: No priority (focus on picks)
        return []
    else:
        # Balanced: Mix
        return ["WR", "CB", "EDGE"]


def generate_team_trades(
    db_path: str,
    dynasty_id: str,
    season: int,
    team_id: int,
    archetype: GMArchetype
) -> List[Dict]:
    """Generate trade proposals for a specific team."""
    philosophy = map_archetype_to_philosophy(archetype)
    budget = map_archetype_to_budget(archetype)
    priority_positions = find_priority_positions(archetype)
    expendable_ids = find_expendable_players(db_path, dynasty_id, season, team_id, archetype)

    directives = OwnerDirectives(
        dynasty_id=dynasty_id,
        team_id=team_id,
        season=season + 1,  # Offseason uses next season
        team_philosophy=philosophy,
        budget_stance=budget,
        priority_positions=priority_positions,
        expendable_player_ids=expendable_ids,
        protected_player_ids=[],
        trust_gm=False,
    )

    try:
        generator = TradeProposalGenerator(
            db_path=db_path,
            dynasty_id=dynasty_id,
            season=season,
            team_id=team_id,
            directives=directives,
        )
        proposals = generator.generate_proposals()
        return [p.to_dict() for p in proposals]
    except Exception as e:
        print(f"    [ERROR] Failed to generate trades: {e}")
        return []


def format_priority(priority: int) -> str:
    """Convert priority tier to string."""
    priority_map = {1: "HIGH", 2: "HIGH", 3: "MEDIUM", 4: "LOW"}
    return priority_map.get(priority, "MEDIUM")


def format_asset(asset: Dict) -> str:
    """Format a single asset for display."""
    asset_type = asset.get("type", "unknown")
    if asset_type == "player":
        name = asset.get("name", "Unknown")
        pos = asset.get("position", "??")
        ovr = asset.get("overall", 0)
        age = asset.get("age", 0)
        cap = asset.get("cap_hit", 0)
        return f"{name} ({pos}, {ovr} OVR) Age {age} • ${cap/1_000_000:.1f}M"
    elif asset_type == "pick":
        year = asset.get("season", asset.get("year", "????"))
        rd = asset.get("round", "?")
        orig = asset.get("original_team", "")
        if orig:
            return f"{year} Round {rd} (via {orig})"
        return f"{year} Round {rd}"
    return str(asset)


def print_proposal(proposal: Dict, index: int):
    """Print a single trade proposal."""
    details = proposal.get("details", {})
    partner = details.get("trade_partner", "Unknown Team")
    sending = details.get("sending", [])
    receiving = details.get("receiving", [])
    value_diff = details.get("value_differential", 0)
    cap_impact = details.get("cap_impact", 0)
    confidence = proposal.get("confidence", 0.5)
    priority = proposal.get("priority", 3)
    reasoning = proposal.get("gm_reasoning", "")

    # Generate title
    recv_names = [a.get("name", "Asset") for a in receiving if a.get("type") == "player"][:2]
    send_names = [a.get("name", "Asset") for a in sending if a.get("type") == "player"][:2]
    if recv_names:
        title = f"Acquire {', '.join(recv_names)} from {partner}"
    elif send_names:
        title = f"Trade {', '.join(send_names)} to {partner}"
    else:
        title = f"Pick Swap with {partner}"

    print(f"\n    [{index}] {title}")
    print(f"        Priority: {format_priority(priority)} | Confidence: {int(confidence * 100)}%")
    print("        " + "-" * 55)

    # Assets
    print("        WE SEND:")
    if sending:
        for asset in sending:
            print(f"          - {format_asset(asset)}")
    else:
        print("          - (nothing)")

    print("        WE RECEIVE:")
    if receiving:
        for asset in receiving:
            print(f"          - {format_asset(asset)}")
    else:
        print("          - (nothing)")

    print("        " + "-" * 55)

    # Value analysis
    value_label = "Favorable" if value_diff > 0 else ("Unfavorable" if value_diff < 0 else "Fair")
    cap_label = f"+${abs(cap_impact)/1_000_000:.1f}M" if cap_impact >= 0 else f"-${abs(cap_impact)/1_000_000:.1f}M"
    print(f"        Value: {value_diff:+d} ({value_label}) | Cap Impact: {cap_label}")

    # GM reasoning (truncate if long)
    if reasoning:
        reasoning_short = reasoning[:100] + "..." if len(reasoning) > 100 else reasoning
        print(f"        Reasoning: \"{reasoning_short}\"")


def group_teams_by_archetype(factory: GMArchetypeFactory) -> Dict[str, List[Tuple[int, GMArchetype]]]:
    """Group all 32 teams by their base archetype name."""
    groups: Dict[str, List[Tuple[int, GMArchetype]]] = defaultdict(list)

    for team_id in range(1, 33):
        try:
            archetype = factory.get_team_archetype(team_id)
            base_name = archetype.name.lower().replace("-", "_").replace(" ", "_")
            groups[base_name].append((team_id, archetype))
        except Exception as e:
            print(f"[WARN] Could not load archetype for team {team_id}: {e}")
            # Default to balanced
            try:
                archetype = factory.get_base_archetype("balanced")
                groups["balanced"].append((team_id, archetype))
            except:
                pass

    return dict(groups)


def run_diagnosis(
    db_path: str,
    dynasty_id: str,
    season: int,
    focus_archetypes: Optional[List[str]] = None,
    focus_teams: Optional[List[int]] = None
) -> Dict[str, Any]:
    """Run the full trade diagnosis."""

    print()
    print("=" * 70)
    print(f"TRADE DIAGNOSIS: Dynasty {dynasty_id} | Season {season}")
    print("=" * 70)

    # Load archetype factory
    factory = GMArchetypeFactory()
    archetype_groups = group_teams_by_archetype(factory)

    # Filter archetypes if specified
    if focus_archetypes:
        filtered = {}
        for arch in focus_archetypes:
            arch_key = arch.lower().replace("-", "_").replace(" ", "_")
            if arch_key in archetype_groups:
                filtered[arch_key] = archetype_groups[arch_key]
            else:
                print(f"[WARN] Archetype '{arch}' not found. Available: {list(archetype_groups.keys())}")
        archetype_groups = filtered

    # Filter teams if specified
    if focus_teams:
        filtered = {}
        for arch_name, teams in archetype_groups.items():
            matching = [(tid, arch) for tid, arch in teams if tid in focus_teams]
            if matching:
                filtered[arch_name] = matching
        archetype_groups = filtered

    # Statistics tracking
    stats = {
        "by_archetype": {},
        "total_proposals": 0,
        "total_teams": 0,
    }

    # Process each archetype group
    for archetype_name, teams in sorted(archetype_groups.items()):
        if not teams:
            continue

        # Get representative archetype for traits display
        _, sample_arch = teams[0]

        print()
        print("=" * 70)
        print(f"ARCHETYPE: {archetype_name.replace('_', ' ').title()} ({len(teams)} teams)")
        print(f"Traits: risk={sample_arch.risk_tolerance:.2f}, "
              f"win_now={sample_arch.win_now_mentality:.2f}, "
              f"draft_value={sample_arch.draft_pick_value:.2f}")
        print("=" * 70)

        arch_stats = {
            "teams": len(teams),
            "proposals": 0,
            "total_value": 0,
            "pick_trades": 0,
            "player_trades": 0,
        }

        for team_id, archetype in teams:
            team_name = get_team_name(team_id)
            philosophy = map_archetype_to_philosophy(archetype)

            print()
            print(f"TEAM: {team_name} (#{team_id})")
            print(f"Philosophy: {philosophy}")
            print("-" * 60)

            proposals = generate_team_trades(db_path, dynasty_id, season, team_id, archetype)

            if not proposals:
                print("    No trade proposals generated.")
            else:
                print(f"    Generated {len(proposals)} proposal(s):")
                for i, proposal in enumerate(proposals, 1):
                    print_proposal(proposal, i)

                    # Track stats
                    details = proposal.get("details", {})
                    arch_stats["proposals"] += 1
                    arch_stats["total_value"] += details.get("value_differential", 0)

                    # Count trade types
                    receiving = details.get("receiving", [])
                    has_player = any(a.get("type") == "player" for a in receiving)
                    has_pick = any(a.get("type") == "pick" for a in receiving)
                    if has_pick and not has_player:
                        arch_stats["pick_trades"] += 1
                    else:
                        arch_stats["player_trades"] += 1

            stats["total_teams"] += 1
            stats["total_proposals"] += len(proposals)

        stats["by_archetype"][archetype_name] = arch_stats

    # Print summary
    print()
    print("=" * 70)
    print("SUMMARY BY ARCHETYPE")
    print("=" * 70)
    print()
    print(f"{'Archetype':<20} | {'Teams':>5} | {'Proposals':>9} | {'Avg Value':>9} | {'Pick Focus':>10}")
    print("-" * 70)

    for arch_name, arch_stats in sorted(stats["by_archetype"].items()):
        teams = arch_stats["teams"]
        proposals = arch_stats["proposals"]
        avg_value = arch_stats["total_value"] / proposals if proposals > 0 else 0
        total_trades = arch_stats["pick_trades"] + arch_stats["player_trades"]
        pick_pct = (arch_stats["pick_trades"] / total_trades * 100) if total_trades > 0 else 0

        print(f"{arch_name.replace('_', ' ').title():<20} | {teams:>5} | {proposals:>9} | {avg_value:>+9.0f} | {pick_pct:>9.0f}%")

    print("-" * 70)
    print(f"{'TOTAL':<20} | {stats['total_teams']:>5} | {stats['total_proposals']:>9}")
    print()
    print("=" * 70)

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Diagnose GM Trade Proposals by Archetype",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    PYTHONPATH=src python demos/trade_diagnosis_demo.py --dynasty testd272ffd3
    PYTHONPATH=src python demos/trade_diagnosis_demo.py --archetype win_now rebuilder
    PYTHONPATH=src python demos/trade_diagnosis_demo.py --team 15 6 30
        """
    )
    parser.add_argument(
        '--dynasty',
        type=str,
        default=None,
        help='Dynasty ID to analyze (default: first dynasty found)'
    )
    parser.add_argument(
        '--use-snapshot',
        action='store_true',
        help='Use existing snapshot instead of creating new one'
    )
    parser.add_argument(
        '--fresh',
        action='store_true',
        help='Force recreate snapshot from current database'
    )
    parser.add_argument(
        '--archetype',
        nargs='+',
        type=str,
        default=None,
        help='Specific archetype(s) to analyze (e.g., win_now rebuilder)'
    )
    parser.add_argument(
        '--team',
        nargs='+',
        type=int,
        default=None,
        help='Specific team ID(s) to analyze (e.g., 15 6 30)'
    )
    args = parser.parse_args()

    # Define paths
    source_db = project_root / "data" / "database" / "game_cycle" / "game_cycle.db"
    snapshot_dir = project_root / "demos" / "snapshots"
    snapshot_db = snapshot_dir / "trade_diagnosis.db"

    print()
    print("=" * 60)
    print("TRADE DIAGNOSIS DEMO")
    print("=" * 60)

    # Step 1: Create/use snapshot
    if not args.use_snapshot:
        if not create_snapshot(source_db, snapshot_db, force=args.fresh):
            return 1
    else:
        if not snapshot_db.exists():
            print(f"ERROR: No snapshot found at {snapshot_db}")
            print("Run without --use-snapshot to create one.")
            return 1
        print(f"Using existing snapshot: {snapshot_db}")

    # Step 2: Get dynasty info
    dynasty_id, season = get_dynasty_info(str(snapshot_db), args.dynasty)
    if not dynasty_id:
        print("\nERROR: No dynasties found in database.")
        return 1

    print(f"\nDynasty: {dynasty_id}")
    print(f"Season: {season}")

    # Step 3: Run diagnosis
    result = run_diagnosis(
        db_path=str(snapshot_db),
        dynasty_id=dynasty_id,
        season=season,
        focus_archetypes=args.archetype,
        focus_teams=args.team
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
