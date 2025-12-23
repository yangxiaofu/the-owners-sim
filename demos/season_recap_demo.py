#!/usr/bin/env python3
"""
Season Recap Demo - Rapid testing of the Season Recap View.

Tests the Season Recap screen that appears after the Super Bowl (OFFSEASON_HONORS stage):
- Super Bowl: Champion and MVP display
- Awards: Full awards/All-Pro/Pro Bowl via embedded AwardsView
- Retirements: Notable retirements with career summaries

Features:
- Loads snapshot with new dynasty_id to avoid conflicts
- Jumps directly to OFFSEASON_HONORS stage
- Launches SeasonRecapView with optional tab selection
- Data verification output for debugging

Usage:
    # Default: Latest snapshot, Super Bowl tab
    python demos/season_recap_demo.py

    # Open to specific tab
    python demos/season_recap_demo.py --tab awards
    python demos/season_recap_demo.py --tab retirements

    # Force fresh snapshot load
    python demos/season_recap_demo.py --fresh

    # Validate data only, skip UI
    python demos/season_recap_demo.py --no-ui


    # Use mock data (no database required)
    python demos/season_recap_demo.py --mock
    python demos/season_recap_demo.py --mock --tab retirements
"""

import sys
import json
import sqlite3
import shutil
import argparse
import uuid
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import Qt

from game_cycle.stage_controller import StageController
from game_cycle.stage_definitions import StageType


# =============================================================================
# Mock Data Generation
# =============================================================================

def create_mock_super_bowl_data() -> Dict[str, Any]:
    """Create realistic mock Super Bowl data for testing."""
    return {
        'champion_team_id': 1,           # Buffalo Bills
        'runner_up_team_id': 30,         # Los Angeles Rams
        'champion_score': 34,
        'runner_up_score': 28,
        'game_id': 'SB_2025_mock',
        'season': 2025,
        'mvp': {
            'name': 'James Cook',
            'position': 'RB',
            'team_id': 1,
            'stats': {
                'rushing_yards': 61,
                'rushing_tds': 2,
                'receiving_yards': 101,
                'receiving_tds': 1,
                'receptions': 6
            }
        }
    }


def create_mock_league_mvp_data() -> Dict[str, Any]:
    """Create realistic mock League MVP data for testing."""
    return {
        'player_name': 'Josh Allen',
        'position': 'QB',
        'team_id': 1,  # Buffalo Bills
    }


def create_mock_retirements_data() -> List[Dict[str, Any]]:
    """Create realistic mock retirements data for testing."""
    return [
        # Notable retirement - HOF-caliber QB
        {
            'player_id': 99001,
            'name': 'Aaron Rodgers',
            'position': 'QB',
            'age': 41,
            'years_played': 19,
            'team_id': 4,           # New York Jets
            'reason': 'age_decline',
            'is_notable': True,
            'headline': '4x MVP Aaron Rodgers announces retirement after illustrious career',
            'career_summary': {
                'mvp_awards': 4,
                'super_bowl_wins': 1,
                'pro_bowls': 10,
                'all_pro_first_team': 4,
                'all_pro_second_team': 1,
                'games_played': 250,
                'pass_yards': 59055,
                'pass_tds': 475,
                'rush_yards': 0,
                'rush_tds': 0,
                'rec_yards': 0,
                'rec_tds': 0,
                'tackles': 0,
                'sacks': 0.0,
                'interceptions': 0,
                'hall_of_fame_score': 95,
                'position': 'QB'
            }
        },
        # Notable retirement - Pro Bowl WR
        {
            'player_id': 99002,
            'name': 'DeAndre Hopkins',
            'position': 'WR',
            'age': 33,
            'years_played': 12,
            'team_id': 12,          # Tennessee Titans
            'reason': 'injury',
            'is_notable': True,
            'headline': 'DeAndre Hopkins retires due to recurring injuries',
            'career_summary': {
                'mvp_awards': 0,
                'super_bowl_wins': 0,
                'pro_bowls': 5,
                'all_pro_first_team': 3,
                'all_pro_second_team': 1,
                'games_played': 180,
                'pass_yards': 0,
                'pass_tds': 0,
                'rush_yards': 0,
                'rush_tds': 0,
                'rec_yards': 12500,
                'rec_tds': 78,
                'tackles': 0,
                'sacks': 0.0,
                'interceptions': 0,
                'hall_of_fame_score': 62,
                'position': 'WR'
            }
        },
        # Non-notable retirement - journeyman LB
        {
            'player_id': 99003,
            'name': 'Mike Johnson',
            'position': 'MLB',
            'age': 32,
            'years_played': 8,
            'team_id': 0,           # Free agent
            'reason': 'released',
            'is_notable': False,
            'headline': 'Mike Johnson retires after being released',
            'career_summary': {
                'mvp_awards': 0,
                'super_bowl_wins': 0,
                'pro_bowls': 0,
                'all_pro_first_team': 0,
                'all_pro_second_team': 0,
                'games_played': 110,
                'pass_yards': 0,
                'pass_tds': 0,
                'rush_yards': 0,
                'rush_tds': 0,
                'rec_yards': 0,
                'rec_tds': 0,
                'tackles': 450,
                'sacks': 8.5,
                'interceptions': 2,
                'hall_of_fame_score': 15,
                'position': 'MLB'
            }
        },
        # Non-notable retirement - backup RB
        {
            'player_id': 99004,
            'name': 'Chris Davis',
            'position': 'RB',
            'age': 30,
            'years_played': 6,
            'team_id': 17,          # Dallas Cowboys
            'reason': 'personal',
            'is_notable': False,
            'headline': 'Chris Davis retires for personal reasons',
            'career_summary': {
                'mvp_awards': 0,
                'super_bowl_wins': 0,
                'pro_bowls': 0,
                'all_pro_first_team': 0,
                'all_pro_second_team': 0,
                'games_played': 85,
                'pass_yards': 0,
                'pass_tds': 0,
                'rush_yards': 2100,
                'rush_tds': 14,
                'rec_yards': 450,
                'rec_tds': 2,
                'tackles': 0,
                'sacks': 0.0,
                'interceptions': 0,
                'hall_of_fame_score': 8,
                'position': 'RB'
            }
        }
    ]


# =============================================================================
# Snapshot Loading Utilities (adapted from offseason_demo.py)
# =============================================================================

def get_tables_with_dynasty_id(conn: sqlite3.Connection) -> List[str]:
    """Get list of all tables that have a dynasty_id column."""
    cursor = conn.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table'
        AND sql LIKE '%dynasty_id%'
        AND name NOT LIKE 'sqlite_%'
    """)
    return [row[0] for row in cursor.fetchall()]


def remap_dynasty_id_inplace(
    db_path: str,
    old_id: str,
    new_id: str,
    new_name: str
) -> None:
    """Remap dynasty_id in all tables (for standalone snapshot)."""
    print(f"  Remapping dynasty_id from '{old_id}' to '{new_id}'...")

    conn = sqlite3.connect(db_path)
    tables = get_tables_with_dynasty_id(conn)
    print(f"    Found {len(tables)} dynasty-specific tables")

    for table in tables:
        try:
            conn.execute(
                f"UPDATE {table} SET dynasty_id = ? WHERE dynasty_id = ?",
                (new_id, old_id)
            )
        except sqlite3.Error as e:
            print(f"    Warning: Failed to update {table}: {e}")

    conn.execute(
        "UPDATE dynasties SET dynasty_name = ? WHERE dynasty_id = ?",
        (new_name, new_id)
    )

    conn.commit()
    conn.close()
    print(f"    Updated {len(tables)} tables")


def load_snapshot_to_new_dynasty(
    snapshot_path: str,
    target_db_path: str,
    new_dynasty_id: Optional[str] = None,
    new_dynasty_name: Optional[str] = None
) -> Tuple[str, int, int]:
    """
    Load snapshot into target database with new dynasty_id.

    Returns:
        Tuple of (dynasty_id, season, user_team_id)
    """
    print(f"Loading snapshot: {snapshot_path}")

    # Load metadata
    metadata_path = Path(snapshot_path).with_suffix('.json')
    if metadata_path.exists():
        with open(metadata_path) as f:
            metadata = json.load(f)
        original_dynasty_id = metadata['dynasty_id']
        season = metadata['season']
        user_team_id = metadata.get('team_id', 1)
        print(f"  Loaded metadata:")
        print(f"    Original Dynasty: {metadata['dynasty_name']}")
        print(f"    Season: {season}, Week: {metadata.get('week', 'N/A')}")
        print(f"    Team ID: {user_team_id}")
    else:
        print("  Metadata JSON not found, querying database...")
        conn = sqlite3.connect(snapshot_path)
        cursor = conn.execute("SELECT dynasty_id, season_year, team_id FROM dynasties LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        if not row:
            raise ValueError("No dynasties found in snapshot database")

        original_dynasty_id = row[0]
        season = row[1]
        user_team_id = row[2] if row[2] else 1
        metadata = {'dynasty_name': original_dynasty_id}

    # Generate new dynasty_id
    if not new_dynasty_id:
        new_dynasty_id = f"demo_recap_{uuid.uuid4().hex[:8]}"

    if not new_dynasty_name:
        new_dynasty_name = f"{metadata['dynasty_name']}_RECAP_DEMO"

    print(f"  New Dynasty: {new_dynasty_name} ({new_dynasty_id})")

    # Copy snapshot to target
    target_path = Path(target_db_path)
    if target_path.exists():
        print(f"  Target database exists, removing...")
        target_path.unlink()

    print(f"  Copying snapshot to {target_path}...")
    shutil.copy2(snapshot_path, target_path)

    # Copy WAL/SHM files if they exist
    for ext in ['-wal', '-shm']:
        wal_source = Path(snapshot_path).with_suffix(Path(snapshot_path).suffix + ext)
        if wal_source.exists():
            shutil.copy2(wal_source, target_path.with_suffix(target_path.suffix + ext))

    # Remap dynasty_id
    remap_dynasty_id_inplace(str(target_path), original_dynasty_id, new_dynasty_id, new_dynasty_name)

    print(f"Snapshot loaded successfully!")

    return (new_dynasty_id, season, user_team_id)


def find_latest_snapshot(snapshot_dir: Path) -> Optional[Path]:
    """Find the latest snapshot file in the snapshots directory."""
    snapshots = sorted(
        snapshot_dir.glob("snapshot_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    return snapshots[0] if snapshots else None


def jump_to_stage(db_path: str, dynasty_id: str, season: int, stage: StageType) -> bool:
    """Jump to specified offseason stage."""
    print(f"\nJumping to stage: {stage.name}...")

    try:
        controller = StageController(db_path, dynasty_id, season)
        current = controller.current_stage
        print(f"  Current stage: {current.display_name if current else 'None'}")

        controller.jump_to_stage(stage)

        print(f"  Jumped to {stage.name}")
        return True

    except Exception as e:
        print(f"  Failed to jump to stage: {e}")
        import traceback
        traceback.print_exc()
        return False


# =============================================================================
# Data Verification
# =============================================================================

def verify_data_requirements(db_path: str, dynasty_id: str, season: int) -> Dict[str, Any]:
    """
    Check that required data exists for Season Recap.

    Returns dict with status for each data requirement.
    """
    from database.unified_api import UnifiedDatabaseAPI
    from game_cycle.database.connection import GameCycleDatabase
    from game_cycle.database.awards_api import AwardsAPI

    results = {
        'super_bowl_game': {'status': False, 'details': None},
        'super_bowl_mvp': {'status': False, 'details': None},
        'season_mvp': {'status': False, 'details': None},
        'retirements': {'status': False, 'count': 0},
    }

    # Check Super Bowl game (week 22, playoffs)
    try:
        unified_api = UnifiedDatabaseAPI(db_path, dynasty_id)
        sb_games = unified_api.games_get_by_week(season, 22, 'playoffs')
        if sb_games:
            game = sb_games[0]
            results['super_bowl_game'] = {
                'status': True,
                'details': f"Game ID: {game.get('game_id', 'N/A')}, "
                          f"Winner: Team {game.get('winner_team_id', 'N/A')}"
            }
    except Exception as e:
        results['super_bowl_game']['details'] = str(e)

    # Check Super Bowl MVP
    try:
        with GameCycleDatabase(db_path) as db:
            awards_api = AwardsAPI(db)
            mvp = awards_api.get_super_bowl_mvp(dynasty_id, season)
            if mvp:
                results['super_bowl_mvp'] = {
                    'status': True,
                    'details': f"{mvp.get('player_name', 'Unknown')} ({mvp.get('position', 'N/A')})"
                }
    except Exception as e:
        results['super_bowl_mvp']['details'] = str(e)

    # Check season MVP
    try:
        with GameCycleDatabase(db_path) as db:
            awards_api = AwardsAPI(db)
            mvp_awards = awards_api.get_award_winners(dynasty_id, season, 'mvp')
            if mvp_awards:
                winner = next((a for a in mvp_awards if a.is_winner), None)
                if winner:
                    results['season_mvp'] = {
                        'status': True,
                        'details': f"Player ID: {winner.player_id}"
                    }
    except Exception as e:
        results['season_mvp']['details'] = str(e)

    # Check retirements (table is retired_players)
    try:
        with GameCycleDatabase(db_path) as db:
            cursor = db.execute(
                "SELECT COUNT(*) FROM retired_players WHERE dynasty_id = ? AND retirement_season = ?",
                (dynasty_id, season)
            )
            count = cursor.fetchone()[0]
            results['retirements'] = {
                'status': count > 0,
                'count': count
            }
    except Exception as e:
        results['retirements']['details'] = str(e)

    return results


def print_data_status(results: Dict[str, Any]):
    """Print data verification results."""
    print("\nData Verification:")
    print("-" * 50)

    for key, info in results.items():
        status = "OK" if info.get('status') else "MISSING"
        icon = "" if info.get('status') else ""
        details = info.get('details') or info.get('count', '')
        print(f"  {icon} {key}: {status}")
        if details:
            print(f"      {details}")

    print("-" * 50)


# =============================================================================
# UI Launch
# =============================================================================

def launch_season_recap_view(
    db_path: str,
    dynasty_id: str,
    season: int,
    user_team_id: int,
    initial_tab: int = 0
):
    """
    Launch SeasonRecapView in a standalone window.

    Args:
        db_path: Path to database
        dynasty_id: Dynasty ID
        season: Season year
        user_team_id: User's team ID
        initial_tab: Tab index (0=Super Bowl, 1=Awards, 2=Retirements)
    """
    from game_cycle_ui.views.season_recap_view import SeasonRecapView

    print(f"\nLaunching SeasonRecapView...")

    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Create main window
    window = QMainWindow()
    tab_names = ['Super Bowl', 'Awards', 'Retirements']
    window.setWindowTitle(
        f"Season Recap Demo - {dynasty_id} Season {season} [{tab_names[initial_tab]}]"
    )
    window.resize(1600, 1000)

    # Create and configure view
    view = SeasonRecapView()
    view.set_context(dynasty_id, db_path, season)

    # Set user team ID if the method exists
    if hasattr(view, 'set_user_team_id'):
        view.set_user_team_id(user_team_id)

    # Refresh data
    view.refresh_data()

    # Switch to requested tab
    view.tabs.setCurrentIndex(initial_tab)

    # Connect signals for debugging
    def on_continue():
        print("[SIGNAL] continue_to_next_stage emitted")

    def on_player_selected(player_id: int):
        print(f"[SIGNAL] player_selected: {player_id}")

    view.continue_to_next_stage.connect(on_continue)
    view.player_selected.connect(on_player_selected)

    window.setCentralWidget(view)
    window.show()

    print(f"  Launched SeasonRecapView (tab: {tab_names[initial_tab]})")

    return app.exec()


def launch_with_mock_data(initial_tab: int = 0):
    """
    Launch SeasonRecapView with mock data (no database required).

    Args:
        initial_tab: Tab index (0=Super Bowl, 1=Awards, 2=Retirements)
    """
    from game_cycle_ui.views.season_recap_view import SeasonRecapView

    print("\nLaunching SeasonRecapView with MOCK DATA...")

    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Create main window
    window = QMainWindow()
    tab_names = ['Super Bowl', 'Awards', 'Retirements']
    window.setWindowTitle(
        f"Season Recap Demo - MOCK DATA [{tab_names[initial_tab]}]"
    )
    window.resize(1600, 1000)

    # Create view - skip database context for mock mode
    view = SeasonRecapView()
    # Don't call set_context() - we'll inject mock data directly
    view._dynasty_id = 'mock_dynasty'
    view._db_path = None
    view._season = 2025
    view.set_user_team_id(1)  # Bills

    # Inject mock data (bypasses database loading)
    print("  Injecting mock Super Bowl data...")
    sb_data = create_mock_super_bowl_data()
    sb_data['league_mvp'] = create_mock_league_mvp_data()
    view.set_super_bowl_data(sb_data)

    print("  Injecting mock retirements data...")
    view.set_retirements(create_mock_retirements_data())

    # Switch to requested tab
    view.tabs.setCurrentIndex(initial_tab)

    # Connect signals for debugging
    def on_continue():
        print("[SIGNAL] continue_to_next_stage emitted")

    def on_player_selected(player_id: int):
        print(f"[SIGNAL] player_selected: {player_id}")

    view.continue_to_next_stage.connect(on_continue)
    view.player_selected.connect(on_player_selected)

    window.setCentralWidget(view)
    window.show()

    print(f"  Launched SeasonRecapView with mock data (tab: {tab_names[initial_tab]})")
    print()
    print("Mock Data Summary:")
    print("  Super Bowl: Bills defeat Rams 34-28")
    print("  SB MVP: James Cook (RB) - 61 rush yds, 2 TD, 101 rec yds, 1 TD")
    print("  League MVP: Josh Allen (QB) - Bills")
    print("  Retirements: 4 total (2 notable, 2 non-notable)")

    return app.exec()


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main entry point for Season Recap demo."""
    parser = argparse.ArgumentParser(
        description="Test Season Recap View with database snapshot or mock data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python demos/season_recap_demo.py --mock             # Use mock data (fastest, no DB needed)
    python demos/season_recap_demo.py --mock --tab retirements
    python demos/season_recap_demo.py --db               # Use main database with seeded data
    python demos/season_recap_demo.py                    # Latest snapshot, Super Bowl tab
    python demos/season_recap_demo.py --tab awards       # Open to Awards tab
    python demos/season_recap_demo.py --fresh            # Force reload snapshot
    python demos/season_recap_demo.py --no-ui            # Validate data only
        """
    )
    parser.add_argument(
        '--mock',
        action='store_true',
        help='Use mock data instead of database (no snapshot required)'
    )
    parser.add_argument(
        '--db',
        action='store_true',
        help='Use main database with seeded data (run seed_season_recap_data.py first)'
    )
    parser.add_argument(
        '--snapshot',
        help='Path to snapshot file (default: latest in demos/snapshots/)'
    )
    parser.add_argument(
        '--tab',
        choices=['super_bowl', 'awards', 'retirements'],
        default='super_bowl',
        help='Initial tab to display (default: super_bowl)'
    )
    parser.add_argument(
        '--fresh',
        action='store_true',
        help='Force reload snapshot (discard existing demo.db)'
    )
    parser.add_argument(
        '--no-ui',
        action='store_true',
        help='Skip UI launch, just validate data'
    )
    parser.add_argument(
        '--team-id',
        type=int,
        help='Override user team ID'
    )
    args = parser.parse_args()

    print("=" * 70)
    print("SEASON RECAP DEMO - Test Super Bowl / Awards / Retirements")
    print("=" * 70)
    print()

    # Map tab name to index
    tab_map = {'super_bowl': 0, 'awards': 1, 'retirements': 2}
    initial_tab = tab_map[args.tab]

    # Handle mock data mode (fastest path, no database needed)
    if args.mock:
        print("MODE: Mock Data (no database required)")
        return launch_with_mock_data(initial_tab)

    # Handle database mode (use main database with seeded data)
    if args.db:
        print("MODE: Main Database (seeded data)")
        db_path = str(project_root / "data" / "database" / "game_cycle" / "game_cycle.db")
        dynasty_id = "test_recap_2025"
        season = 2025
        user_team_id = 1  # Bills

        # Verify dynasty exists
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.execute(
                "SELECT dynasty_name FROM dynasties WHERE dynasty_id = ?",
                (dynasty_id,)
            )
            row = cursor.fetchone()
            conn.close()

            if not row:
                print(f"\nERROR: Dynasty '{dynasty_id}' not found in database.")
                print("Run the seed script first:")
                print("  PYTHONPATH=src python demos/seed_season_recap_data.py")
                return 1

            print(f"  Dynasty: {row[0]} ({dynasty_id})")
            print(f"  Season: {season}")
            print()
        except Exception as e:
            print(f"\nERROR: {e}")
            return 1

        # Verify data
        data_status = verify_data_requirements(db_path, dynasty_id, season)
        print_data_status(data_status)

        if args.no_ui:
            print("\nSkipping UI (--no-ui specified)")
            return 0

        return launch_season_recap_view(db_path, dynasty_id, season, user_team_id, initial_tab)

    # Find snapshot
    snapshot_path = args.snapshot
    if not snapshot_path:
        snapshots_dir = Path(__file__).parent / "snapshots"
        snapshot = find_latest_snapshot(snapshots_dir)

        if not snapshot:
            print("ERROR: No snapshots found in demos/snapshots/")
            print()
            print("Create a snapshot first with:")
            print("  PYTHONPATH=src python scripts/create_dynasty_snapshot.py --dynasty-id YOUR_DYNASTY_ID")
            print()
            return 1

        snapshot_path = str(snapshot)
        print(f"Using latest snapshot: {snapshot_path}")
        print()

    # Define target database (demo-specific)
    demo_db_path = str(Path(__file__).parent / "snapshots" / "season_recap_demo.db")

    # Load snapshot (or use existing if --fresh not specified)
    if args.fresh or not Path(demo_db_path).exists():
        try:
            dynasty_id, season, user_team_id = load_snapshot_to_new_dynasty(
                snapshot_path,
                demo_db_path,
                new_dynasty_id="demo_season_recap",
                new_dynasty_name="Season Recap Demo"
            )
            print()
        except Exception as e:
            print(f"\nERROR loading snapshot: {e}")
            import traceback
            traceback.print_exc()
            return 1
    else:
        # Get existing dynasty info
        print(f"Using existing demo database: {demo_db_path}")
        try:
            conn = sqlite3.connect(demo_db_path)
            cursor = conn.execute("SELECT dynasty_id, season_year, team_id FROM dynasties LIMIT 1")
            row = cursor.fetchone()
            conn.close()

            if not row:
                print("ERROR: No dynasties found in demo database")
                print("Run with --fresh to reload snapshot")
                return 1

            dynasty_id, season, user_team_id = row[0], row[1], row[2] or 1
            print(f"  Dynasty: {dynasty_id} (Season {season}, Team {user_team_id})")
            print()
        except Exception as e:
            print(f"ERROR reading demo database: {e}")
            print("Run with --fresh to reload snapshot")
            return 1

    # Override team ID if specified
    if args.team_id:
        user_team_id = args.team_id
        print(f"Using team ID override: {user_team_id}")

    # Jump to OFFSEASON_HONORS stage
    if not jump_to_stage(demo_db_path, dynasty_id, season, StageType.OFFSEASON_HONORS):
        print("\nWarning: Failed to jump to stage, but continuing...")

    # Verify data requirements
    data_status = verify_data_requirements(demo_db_path, dynasty_id, season)
    print_data_status(data_status)

    # Launch UI (unless --no-ui)
    if args.no_ui:
        print("\nSkipping UI (--no-ui specified)")
        print(f"Database: {demo_db_path}")
        print(f"Dynasty: {dynasty_id}")
        print(f"Season: {season}")
        return 0

    return launch_season_recap_view(
        demo_db_path, dynasty_id, season, user_team_id, initial_tab
    )


if __name__ == "__main__":
    sys.exit(main())
