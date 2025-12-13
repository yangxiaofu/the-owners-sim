#!/usr/bin/env python3
"""
Awards Demo - Test award system with database snapshot.

This demo allows rapid iteration on the awards system without simulating
an entire season. It:
1. Creates a snapshot of your current game_cycle database
2. Jumps directly to the OFFSEASON_HONORS stage
3. Executes awards calculation
4. Opens the Awards View UI for testing

Usage:
    python demos/awards_demo.py           # Use existing snapshot or create new
    python demos/awards_demo.py --fresh   # Force recreate snapshot from current DB
"""

import sys
import shutil
import argparse
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import Qt

from game_cycle.stage_controller import StageController
from game_cycle.stage_definitions import StageType
from game_cycle_ui.views.awards_view import AwardsView
from game_cycle_ui.controllers.dynasty_controller import GameCycleDynastyController


def create_snapshot(source_db: Path, snapshot_db: Path, force: bool = False) -> bool:
    """Create database snapshot if needed."""
    if not source_db.exists():
        print(f"ERROR: Source database not found: {source_db}")
        return False

    if force or not snapshot_db.exists():
        print(f"Creating snapshot from {source_db}...")
        # Ensure parent directory exists
        snapshot_db.parent.mkdir(parents=True, exist_ok=True)
        # Copy database (and any WAL/SHM files)
        shutil.copy2(source_db, snapshot_db)
        # Also copy WAL files if they exist
        for ext in ['-wal', '-shm']:
            wal_source = source_db.with_suffix(source_db.suffix + ext)
            if wal_source.exists():
                shutil.copy2(wal_source, snapshot_db.with_suffix(snapshot_db.suffix + ext))
        print(f"Snapshot created: {snapshot_db}")
    else:
        print(f"Using existing snapshot: {snapshot_db}")
    return True


def get_dynasty_info(db_path: str) -> tuple:
    """Get dynasty_id and season from database."""
    gc_controller = GameCycleDynastyController(db_path)
    dynasties = gc_controller.list_dynasties()

    if not dynasties:
        return None, None

    # Use first dynasty
    dynasty = dynasties[0]
    dynasty_id = dynasty['dynasty_id']

    # Try to get current season from dynasty
    season = dynasty.get('current_season')
    if not season:
        # Default to 2025 if not found
        season = 2025

    return dynasty_id, season


def execute_awards(db_path: str, dynasty_id: str, season: int) -> dict:
    """Jump to awards stage and execute calculation."""
    print(f"\nInitializing StageController...")
    print(f"  Database: {db_path}")
    print(f"  Dynasty: {dynasty_id}")
    print(f"  Season: {season}")

    controller = StageController(db_path, dynasty_id, season)

    print(f"\nCurrent stage: {controller.current_stage.display_name if controller.current_stage else 'None'}")
    print(f"Jumping to OFFSEASON_HONORS...")

    controller.jump_to_stage(StageType.OFFSEASON_HONORS)

    print(f"Executing awards calculation...")
    result = controller.execute_current_stage()

    print(f"\nResults:")
    print(f"  Success: {result.success}")
    print(f"  Events processed: {len(result.events_processed)}")
    if result.errors:
        print(f"  Errors: {result.errors}")

    # Also calculate All-Pro, Pro Bowl, and Stat Leaders (not done by stage controller)
    print(f"\nCalculating All-Pro, Pro Bowl, and Stat Leaders...")
    from game_cycle.services.awards_service import AwardsService
    service = AwardsService(db_path, dynasty_id, season)

    all_pro = service.select_all_pro_teams()
    print(f"  All-Pro: {all_pro.total_selections} selections")

    pro_bowl = service.select_pro_bowl_rosters()
    print(f"  Pro Bowl: {pro_bowl.total_selections} selections")

    stat_leaders = service.record_statistical_leaders()
    print(f"  Stat Leaders: {stat_leaders.total_recorded} records")

    return {
        'success': result.success,
        'events': result.events_processed,
        'errors': result.errors
    }


def launch_ui(db_path: str, dynasty_id: str, season: int):
    """Launch Qt application with AwardsView."""
    print(f"\nLaunching Awards UI...")

    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Create main window
    window = QMainWindow()
    window.setWindowTitle(f"Awards Demo - {dynasty_id} Season {season}")
    window.resize(1400, 900)

    # Create and configure awards view
    awards_view = AwardsView()
    awards_view.set_context(dynasty_id, db_path, season)
    awards_view.refresh_data()

    window.setCentralWidget(awards_view)
    window.show()

    return app.exec()


def main():
    parser = argparse.ArgumentParser(
        description="Test award system with database snapshot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python demos/awards_demo.py           # Use existing snapshot
    python demos/awards_demo.py --fresh   # Create fresh snapshot
    python demos/awards_demo.py --skip-calc  # Skip calculation, just show UI
        """
    )
    parser.add_argument(
        '--fresh',
        action='store_true',
        help='Force recreate snapshot from current database'
    )
    parser.add_argument(
        '--skip-calc',
        action='store_true',
        help='Skip awards calculation, just show existing awards in UI'
    )
    args = parser.parse_args()

    # Define paths
    source_db = project_root / "data" / "database" / "game_cycle" / "game_cycle.db"
    snapshot_dir = project_root / "demos" / "snapshots"
    snapshot_db = snapshot_dir / "game_cycle_snapshot.db"

    print("=" * 60)
    print("AWARDS DEMO - Database Snapshot Testing")
    print("=" * 60)

    # Step 1: Create snapshot
    if not create_snapshot(source_db, snapshot_db, force=args.fresh):
        return 1

    # Step 2: Get dynasty info
    dynasty_id, season = get_dynasty_info(str(snapshot_db))
    if not dynasty_id:
        print("\nERROR: No dynasties found in database.")
        print("Run main2.py first to create a dynasty and simulate a season.")
        return 1

    print(f"\nDynasty: {dynasty_id}")
    print(f"Season: {season}")

    # Step 3: Execute awards calculation (unless skipped)
    if not args.skip_calc:
        result = execute_awards(str(snapshot_db), dynasty_id, season)
        if not result['success']:
            print("\nWARNING: Awards calculation had issues. UI may show incomplete data.")
    else:
        print("\nSkipping awards calculation (--skip-calc)")

    # Step 4: Launch UI
    return launch_ui(str(snapshot_db), dynasty_id, season)


if __name__ == "__main__":
    sys.exit(main())
