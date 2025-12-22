#!/usr/bin/env python3
"""
Awards Diagnosis Demo - Debug All-Pro and Pro Bowl Selection Algorithms.

This demo isolates the awards selection algorithms to diagnose why backup
players might be incorrectly selected for All-Pro or Pro Bowl teams.

Usage:
    PYTHONPATH=src python demos/awards_diagnosis_demo.py --dynasty testd272ffd3
    PYTHONPATH=src python demos/awards_diagnosis_demo.py --use-snapshot
    PYTHONPATH=src python demos/awards_diagnosis_demo.py --position RB
"""

import sys
import shutil
import argparse
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Set

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from game_cycle.database.connection import GameCycleDatabase
from game_cycle.database.analytics_api import AnalyticsAPI
from game_cycle.database.awards_api import AwardsAPI
from game_cycle_ui.controllers.dynasty_controller import GameCycleDynastyController
from statistics.stats_api import StatsAPI


# Eligibility thresholds (mirrored from eligibility.py)
MINIMUM_GAMES = 12
MINIMUM_SNAPS = 100  # Base minimum

# Position-specific snap minimums (mirrored from eligibility.py)
POSITION_SNAP_MINIMUMS = {
    # Offense - High volume
    'QB': 500, 'LT': 500, 'LG': 500, 'C': 500, 'RG': 500, 'RT': 500,
    # Offense - Medium volume
    'WR': 400, 'TE': 150, 'RB': 150, 'FB': 100,
    # Defense - High volume
    'EDGE': 400, 'DE': 400, 'DT': 400, 'CB': 400, 'FS': 400, 'SS': 400,
    # Defense - Medium volume
    'LOLB': 300, 'MLB': 300, 'ROLB': 300, 'LB': 300, 'ILB': 300, 'OLB': 300,
    # Special teams
    'K': 50, 'P': 50, 'LS': 50,
}

# Position-specific stat minimums
STAT_MINIMUMS = {
    'QB': {'passing_attempts': 224},
    'RB': {'rushing_attempts': 100, 'total_touches': 150},  # OR condition
    'WR': {'receptions': 28, 'receiving_targets': 50},  # OR condition
    'TE': {'receptions': 20},
    'EDGE': {'tackles_total': 25, 'sacks': 3.0},  # OR condition
    'DT': {'tackles_total': 30, 'sacks': 2.0},  # OR condition
    'LOLB': {'tackles_total': 40},
    'MLB': {'tackles_total': 40},
    'ROLB': {'tackles_total': 40},
    'CB': {'defensive_snaps': 400, 'interceptions': 1},  # OR condition
    'FS': {'tackles_total': 30, 'interceptions': 1},  # OR condition
    'SS': {'tackles_total': 30, 'interceptions': 1},  # OR condition
}

# Position groups for display (use database format: full names)
POSITION_ORDER = [
    # Offense
    'quarterback', 'running_back', 'fullback', 'wide_receiver', 'tight_end',
    'left_tackle', 'left_guard', 'center', 'right_guard', 'right_tackle',
    # Defense
    'defensive_end', 'defensive_tackle',
    'outside_linebacker', 'inside_linebacker', 'middle_linebacker', 'linebacker',
    'cornerback', 'free_safety', 'strong_safety', 'safety',
    # Special teams
    'kicker', 'punter',
]

# Map database position names to abbreviations for eligibility checks
POSITION_ABBREV_MAP = {
    'quarterback': 'QB',
    'running_back': 'RB',
    'fullback': 'FB',
    'wide_receiver': 'WR',
    'tight_end': 'TE',
    'left_tackle': 'LT',
    'left_guard': 'LG',
    'center': 'C',
    'right_guard': 'RG',
    'right_tackle': 'RT',
    'defensive_end': 'EDGE',
    'defensive_tackle': 'DT',
    'outside_linebacker': 'LOLB',
    'inside_linebacker': 'MLB',
    'middle_linebacker': 'MLB',
    'linebacker': 'LB',
    'mike_linebacker': 'MLB',
    'will_linebacker': 'LOLB',
    'cornerback': 'CB',
    'free_safety': 'FS',
    'strong_safety': 'SS',
    'safety': 'SS',
    'kicker': 'K',
    'punter': 'P',
}

# Reverse map for CLI input
ABBREV_TO_FULL = {v: k for k, v in POSITION_ABBREV_MAP.items()}


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


def get_dynasty_info(db_path: str, target_dynasty_id: Optional[str] = None) -> tuple:
    """Get dynasty_id and season from database."""
    gc_controller = GameCycleDynastyController(db_path)
    dynasties = gc_controller.list_dynasties()

    if not dynasties:
        return None, None

    # Find matching dynasty or use first
    if target_dynasty_id:
        for d in dynasties:
            if d['dynasty_id'].lower() == target_dynasty_id.lower():
                return d['dynasty_id'], d.get('current_season', 2025)
        print(f"Warning: Dynasty '{target_dynasty_id}' not found, using first dynasty")

    dynasty = dynasties[0]
    return dynasty['dynasty_id'], dynasty.get('current_season', 2025)


# Load team data once at module level
_TEAM_ABBREVS: Dict[int, str] = {}


def _load_team_abbreviations():
    """Load team abbreviations from teams.json."""
    global _TEAM_ABBREVS
    if _TEAM_ABBREVS:
        return
    teams_file = project_root / "src" / "data" / "teams.json"
    try:
        with open(teams_file) as f:
            data = json.load(f)
            for tid, team in data.get("teams", {}).items():
                _TEAM_ABBREVS[int(tid)] = team.get("abbreviation", f"T{tid}")
    except Exception:
        pass


def get_team_abbrev(team_id: int) -> str:
    """Get team abbreviation from ID."""
    _load_team_abbreviations()
    return _TEAM_ABBREVS.get(team_id, f"T{team_id}")


def check_eligibility(candidate: Dict, stats: Dict, position: str) -> tuple:
    """
    Check player eligibility with detailed breakdown.

    Args:
        candidate: Candidate data dict
        stats: Player stats dict
        position: Full position name (e.g., 'running_back')

    Returns:
        Tuple of (is_eligible, list of failure reasons)
    """
    reasons = []

    # Check games played
    games = candidate.get('games_graded', 0)
    if games < MINIMUM_GAMES:
        reasons.append(f"Games {games} < {MINIMUM_GAMES}")

    # Check position-specific snap minimum
    pos_abbrev = POSITION_ABBREV_MAP.get(position, position).upper()
    min_snaps = POSITION_SNAP_MINIMUMS.get(pos_abbrev, MINIMUM_SNAPS)
    snaps = candidate.get('total_snaps', 0)
    if snaps < min_snaps:
        reasons.append(f"Snaps {snaps} < {min_snaps}")

    # Convert to abbreviation for stat minimums check
    pos = POSITION_ABBREV_MAP.get(position, position).upper()
    if pos in STAT_MINIMUMS:
        mins = STAT_MINIMUMS[pos]

        if pos == 'QB':
            attempts = stats.get('passing_attempts', 0)
            if attempts < mins['passing_attempts']:
                reasons.append(f"PassAtt {attempts} < {mins['passing_attempts']}")

        elif pos == 'RB':
            carries = stats.get('rushing_attempts', 0)
            receptions = stats.get('receptions', 0)
            total = carries + receptions
            if carries < mins['rushing_attempts'] and total < mins['total_touches']:
                reasons.append(f"Carries {carries} < {mins['rushing_attempts']} AND Touches {total} < {mins['total_touches']}")

        elif pos == 'WR':
            receptions = stats.get('receptions', 0)
            targets = stats.get('receiving_targets', 0)
            if receptions < mins['receptions'] and targets < mins['receiving_targets']:
                reasons.append(f"Rec {receptions} < {mins['receptions']} AND Targets {targets} < {mins['receiving_targets']}")

        elif pos == 'TE':
            receptions = stats.get('receptions', 0)
            if receptions < mins['receptions']:
                reasons.append(f"Rec {receptions} < {mins['receptions']}")

        elif pos in ('EDGE', 'DT'):
            tackles = stats.get('tackles_total', 0)
            sacks = stats.get('sacks', 0.0)
            if tackles < mins['tackles_total'] and sacks < mins['sacks']:
                reasons.append(f"Tackles {tackles} < {mins['tackles_total']} AND Sacks {sacks} < {mins['sacks']}")

        elif pos in ('LOLB', 'MLB', 'ROLB'):
            tackles = stats.get('tackles_total', 0)
            if tackles < mins['tackles_total']:
                reasons.append(f"Tackles {tackles} < {mins['tackles_total']}")

        elif pos == 'CB':
            snaps = stats.get('defensive_snaps', stats.get('total_snaps', 0))
            ints = stats.get('interceptions', 0)
            if snaps < mins['defensive_snaps'] and ints < mins['interceptions']:
                reasons.append(f"DefSnaps {snaps} < {mins['defensive_snaps']} AND INTs {ints} < {mins['interceptions']}")

        elif pos in ('FS', 'SS'):
            tackles = stats.get('tackles_total', 0)
            ints = stats.get('interceptions', 0)
            if tackles < mins['tackles_total'] and ints < mins['interceptions']:
                reasons.append(f"Tackles {tackles} < {mins['tackles_total']} AND INTs {ints} < {mins['interceptions']}")

    return (len(reasons) == 0, reasons)


def format_stat_columns(position: str, candidate: Dict, stats: Dict) -> str:
    """Format position-specific stat columns."""
    pos = POSITION_ABBREV_MAP.get(position, position).upper()

    if pos == 'QB':
        return f"{stats.get('passing_attempts', 0):>4} | {candidate.get('passing_yards', 0):>5} | {candidate.get('passing_tds', 0):>3}"

    elif pos == 'RB':
        carries = stats.get('rushing_attempts', 0)
        receptions = candidate.get('receptions', 0)
        total = carries + receptions
        rush_yds = candidate.get('rushing_yards', 0)
        return f"{carries:>4} | {receptions:>3} | {total:>4} | {rush_yds:>5}"

    elif pos in ('WR', 'TE'):
        rec = candidate.get('receptions', 0)
        targets = stats.get('receiving_targets', 0)
        rec_yds = candidate.get('receiving_yards', 0)
        return f"{rec:>4} | {targets:>4} | {rec_yds:>5}"

    elif pos in ('EDGE', 'DT'):
        tackles = candidate.get('tackles_total', 0)
        sacks = candidate.get('sacks', 0.0)
        return f"{tackles:>4} | {sacks:>5.1f}"

    elif pos in ('LOLB', 'MLB', 'ROLB', 'LB'):
        tackles = candidate.get('tackles_total', 0)
        return f"{tackles:>4}"

    elif pos == 'CB':
        tackles = candidate.get('tackles_total', 0)
        ints = candidate.get('interceptions', 0)
        return f"{tackles:>4} | {ints:>3}"

    elif pos in ('FS', 'SS'):
        tackles = candidate.get('tackles_total', 0)
        ints = candidate.get('interceptions', 0)
        return f"{tackles:>4} | {ints:>3}"

    else:
        return "-"


def get_stat_header(position: str) -> str:
    """Get column headers for position-specific stats."""
    pos = POSITION_ABBREV_MAP.get(position, position).upper()

    if pos == 'QB':
        return " Att | PassY |  TD"
    elif pos == 'RB':
        return "Rush | Rec | Totl | RushY"
    elif pos in ('WR', 'TE'):
        return " Rec | Targ | RecY"
    elif pos in ('EDGE', 'DT'):
        return "Tckl | Sacks"
    elif pos in ('LOLB', 'MLB', 'ROLB', 'LB'):
        return "Tckl"
    elif pos in ('CB', 'FS', 'SS'):
        return "Tckl | INT"
    else:
        return "Stats"


def run_diagnosis(
    db_path: str,
    dynasty_id: str,
    season: int,
    focus_positions: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Run the full awards diagnosis."""

    print("=" * 100)
    print(f"AWARDS DIAGNOSIS: Dynasty {dynasty_id} | Season {season}")
    print("=" * 100)

    # Initialize APIs
    db = GameCycleDatabase(db_path)
    analytics_api = AnalyticsAPI(db_path)
    awards_api = AwardsAPI(db)
    stats_api = StatsAPI(db_path, dynasty_id)

    # Get actual selections
    all_pro_teams = awards_api.get_all_pro_teams(dynasty_id, season)
    pro_bowl_roster = awards_api.get_pro_bowl_roster(dynasty_id, season)

    # Build selection lookup
    all_pro_1st: Set[int] = {s.player_id for s in all_pro_teams.get('FIRST_TEAM', [])}
    all_pro_2nd: Set[int] = {s.player_id for s in all_pro_teams.get('SECOND_TEAM', [])}
    pro_bowl_all: Set[int] = set()
    for conf_players in pro_bowl_roster.values():
        pro_bowl_all.update(s.player_id for s in conf_players)

    # Get all candidates - use min_snaps=1 to include ALL players for diagnosis
    # (The production code now properly filters by snaps, but we want to see
    # all players including those who shouldn't have been selected)
    candidates = analytics_api.get_top_candidates_by_position(
        dynasty_id=dynasty_id,
        season=season,
        min_games=1,  # Get all players for analysis
        min_snaps=1,  # Include low-snap players for anomaly detection
        per_position_limit=30  # More candidates for diagnosis
    )

    # Group by position
    by_position: Dict[str, List[Dict]] = {}
    for c in candidates:
        pos = c['position']
        if pos not in by_position:
            by_position[pos] = []
        by_position[pos].append(c)

    # Determine positions to analyze
    positions_to_check = focus_positions if focus_positions else POSITION_ORDER

    total_anomalies = 0
    anomaly_details = []

    for position in positions_to_check:
        if position not in by_position:
            continue

        pos_candidates = by_position[position]
        # Sort by grade descending
        pos_candidates.sort(key=lambda x: x.get('overall_grade', 0), reverse=True)

        # Get top 15 for display
        top_candidates = pos_candidates[:15]

        # Get additional stats for each candidate
        enriched = []
        for c in top_candidates:
            player_id = c['player_id']
            stats = stats_api.get_player_season_stats(str(player_id), season) or {}
            is_eligible, fail_reasons = check_eligibility(c, stats, position)

            # Determine selection (can have multiple)
            selections = []
            if player_id in all_pro_1st:
                selections.append("AP1")
            if player_id in all_pro_2nd:
                selections.append("AP2")
            if player_id in pro_bowl_all:
                selections.append("PB")
            selection = "+".join(selections) if selections else ""

            # Check for anomaly
            is_anomaly = selection and not is_eligible
            if is_anomaly:
                total_anomalies += 1
                anomaly_details.append({
                    'position': position,
                    'player_name': c.get('player_name', f"Player {player_id}"),
                    'team': get_team_abbrev(c.get('team_id', 0)),
                    'selection': selection,
                    'reasons': fail_reasons
                })

            enriched.append({
                **c,
                'stats': stats,
                'is_eligible': is_eligible,
                'fail_reasons': fail_reasons,
                'selection': selection,
                'is_anomaly': is_anomaly
            })

        # Print position section
        pos_abbrev = POSITION_ABBREV_MAP.get(position, position.upper())
        print()
        print("=" * 100)
        print(f"POSITION: {pos_abbrev} ({position})")

        # Show thresholds with position-specific snap minimum
        min_snaps = POSITION_SNAP_MINIMUMS.get(pos_abbrev, MINIMUM_SNAPS)
        if pos_abbrev in STAT_MINIMUMS:
            mins = STAT_MINIMUMS[pos_abbrev]
            thresh_parts = [f"{k}:{v}" for k, v in mins.items()]
            print(f"Thresholds: Games >= {MINIMUM_GAMES}, Snaps >= {min_snaps}, {', '.join(thresh_parts)}")
        else:
            print(f"Thresholds: Games >= {MINIMUM_GAMES}, Snaps >= {min_snaps}")
        print("-" * 100)

        # Print header
        stat_header = get_stat_header(position)
        print(f"Rank | {'Player':<22} | Team | Games | Snaps | {stat_header:<20} | Grade | Elig | Select")
        print("-" * 100)

        # Print candidates
        for rank, e in enumerate(enriched[:12], 1):
            name = e.get('player_name', 'Unknown')[:22]
            team = get_team_abbrev(e.get('team_id', 0))
            games = e.get('games_graded', 0)
            snaps = e.get('total_snaps', 0)
            grade = e.get('overall_grade', 0.0)
            stats = e.get('stats', {})

            stat_cols = format_stat_columns(position, e, stats)
            elig = "PASS" if e['is_eligible'] else "FAIL"
            selection = e['selection'] or "-"
            anomaly_marker = " <-- ANOMALY" if e['is_anomaly'] else ""

            print(f"{rank:>4} | {name:<22} | {team:<4} | {games:>5} | {snaps:>5} | {stat_cols:<20} | {grade:>5.1f} | {elig:<4} | {selection:<6}{anomaly_marker}")

        # Print failure reasons for ineligible players
        failed = [e for e in enriched if not e['is_eligible']]
        if failed:
            print()
            print("* Ineligible Players:")
            for e in failed[:5]:
                name = e.get('player_name', 'Unknown')
                reasons = ", ".join(e['fail_reasons'])
                print(f"  - {name}: {reasons}")

        # Show SELECTED players for this position (may not be in top 12 by grade)
        # Find all selected players from the full candidate list
        selected_ids = set()
        for pid in all_pro_1st:
            selected_ids.add(pid)
        for pid in all_pro_2nd:
            selected_ids.add(pid)
        for pid in pro_bowl_all:
            selected_ids.add(pid)

        # Get selected players for this position from full candidate list
        selected_for_pos = []
        for c in pos_candidates:
            player_id = c['player_id']
            if player_id in selected_ids:
                stats = stats_api.get_player_season_stats(str(player_id), season) or {}
                selections = []
                if player_id in all_pro_1st:
                    selections.append("AP1")
                if player_id in all_pro_2nd:
                    selections.append("AP2")
                if player_id in pro_bowl_all:
                    selections.append("PB")
                selection = "+".join(selections) if selections else ""
                if selection:
                    selected_for_pos.append({
                        **c,
                        'stats': stats,
                        'selection': selection,
                    })

        if selected_for_pos:
            # Sort by selection priority: AP1 > AP2 > PB (check first part of combined selections)
            def get_priority(sel):
                if 'AP1' in sel:
                    return 0
                elif 'AP2' in sel:
                    return 1
                elif 'PB' in sel:
                    return 2
                return 3
            selected_for_pos.sort(key=lambda x: get_priority(x['selection']))

            print()
            print(f">>> SELECTED PLAYERS for {pos_abbrev}:")
            print("-" * 100)
            print(f"     | {'Player':<22} | Team | Games | Snaps | {stat_header:<20} | Grade | Select")
            print("-" * 100)
            for e in selected_for_pos:
                name = e.get('player_name', 'Unknown')[:22]
                team = get_team_abbrev(e.get('team_id', 0))
                games = e.get('games_graded', 0)
                snaps = e.get('total_snaps', 0)
                grade = e.get('overall_grade', 0.0)
                stats = e.get('stats', {})
                stat_cols = format_stat_columns(position, e, stats)
                selection = e['selection']
                print(f"     | {name:<22} | {team:<4} | {games:>5} | {snaps:>5} | {stat_cols:<20} | {grade:>5.1f} | {selection}")

    # Summary section
    print()
    print("=" * 100)
    print("DIAGNOSIS SUMMARY")
    print("=" * 100)
    print()
    print(f"Total All-Pro 1st Team: {len(all_pro_1st)}")
    print(f"Total All-Pro 2nd Team: {len(all_pro_2nd)}")
    print(f"Total Pro Bowl: {len(pro_bowl_all)}")
    print()

    if total_anomalies > 0:
        print(f"ANOMALIES DETECTED: {total_anomalies}")
        print("-" * 50)
        for a in anomaly_details:
            reasons = ", ".join(a['reasons'])
            print(f"  [{a['selection']}] {a['player_name']} ({a['team']}, {a['position']}): {reasons}")
    else:
        print("NO ANOMALIES DETECTED - All selections meet eligibility criteria")

    print()
    print("=" * 100)

    return {
        'total_anomalies': total_anomalies,
        'anomalies': anomaly_details,
        'all_pro_count': len(all_pro_1st) + len(all_pro_2nd),
        'pro_bowl_count': len(pro_bowl_all)
    }


def main():
    parser = argparse.ArgumentParser(
        description="Diagnose Awards Selection Algorithm",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    PYTHONPATH=src python demos/awards_diagnosis_demo.py --dynasty testd272ffd3
    PYTHONPATH=src python demos/awards_diagnosis_demo.py --use-snapshot
    PYTHONPATH=src python demos/awards_diagnosis_demo.py --position RB WR
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
        '--position',
        nargs='+',
        type=str,
        default=None,
        help='Specific position(s) to analyze (e.g., RB WR)'
    )
    args = parser.parse_args()

    # Define paths
    source_db = project_root / "data" / "database" / "game_cycle" / "game_cycle.db"
    snapshot_dir = project_root / "demos" / "snapshots"
    snapshot_db = snapshot_dir / "awards_diagnosis.db"

    print()
    print("=" * 60)
    print("AWARDS DIAGNOSIS DEMO")
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

    # Normalize position args - convert abbreviations to full names
    focus_positions = None
    if args.position:
        focus_positions = []
        for p in args.position:
            p_upper = p.upper()
            # Check if it's an abbreviation that needs conversion
            if p_upper in ABBREV_TO_FULL:
                focus_positions.append(ABBREV_TO_FULL[p_upper])
            else:
                # Might already be a full name
                focus_positions.append(p.lower())
        print(f"Focus positions: {', '.join(focus_positions)}")

    # Step 3: Run diagnosis
    result = run_diagnosis(
        db_path=str(snapshot_db),
        dynasty_id=dynasty_id,
        season=season,
        focus_positions=focus_positions
    )

    return 0 if result['total_anomalies'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
