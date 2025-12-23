#!/usr/bin/env python3
"""
Offseason Demo - Rapid Offseason Feature Testing

Loads a database snapshot and jumps directly to any offseason stage for rapid testing.
Avoids having to simulate through 18+ weeks of regular season each time.

Features:
- Loads snapshot with new dynasty_id to avoid conflicts
- Jumps to any offseason stage (HONORS, FREE_AGENCY, DRAFT, etc.)
- Launches appropriate UI view for testing
- Separate demo database (doesn't pollute main game_cycle.db)

Usage:
    # Use latest snapshot, start at Honors
    python demos/offseason_demo.py

    # Jump to specific stage
    python demos/offseason_demo.py --stage OFFSEASON_FREE_AGENCY

    # Use specific snapshot
    python demos/offseason_demo.py --snapshot demos/snapshots/snapshot_*.db

    # Force fresh load (discard existing demo)
    python demos/offseason_demo.py --fresh
"""

import sys
import json
import sqlite3
import shutil
import argparse
import uuid
from pathlib import Path
from typing import Optional, Tuple, List

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PySide6.QtCore import Qt

from game_cycle.stage_controller import StageController
from game_cycle.stage_definitions import StageType
from game_cycle_ui.controllers.dynasty_controller import GameCycleDynastyController


def get_tables_with_dynasty_id(conn: sqlite3.Connection) -> List[str]:
    """
    Get list of all tables that have a dynasty_id column.

    Args:
        conn: Database connection

    Returns:
        List of table names
    """
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
    """
    Remap dynasty_id in all tables (for standalone snapshot).

    Updates dynasties table and all dynasty-specific tables.

    Args:
        db_path: Path to database
        old_id: Original dynasty ID
        new_id: New dynasty ID
        new_name: New dynasty name
    """
    print(f"  ✓ Remapping dynasty_id from '{old_id}' to '{new_id}'...")

    conn = sqlite3.connect(db_path)

    # Get all tables with dynasty_id column
    tables = get_tables_with_dynasty_id(conn)
    print(f"    Found {len(tables)} dynasty-specific tables")

    # Update each table
    for table in tables:
        try:
            conn.execute(
                f"UPDATE {table} SET dynasty_id = ? WHERE dynasty_id = ?",
                (new_id, old_id)
            )
        except sqlite3.Error as e:
            print(f"    Warning: Failed to update {table}: {e}")

    # Update dynasty name
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
) -> Tuple[str, int]:
    """
    Load snapshot into target database with new dynasty_id to avoid conflicts.

    Process:
    1. Load snapshot metadata from JSON
    2. Generate new dynasty_id if not provided
    3. Copy snapshot to target DB (creating if not exists)
    4. Remap dynasty_id in all dynasty-specific tables
    5. Return (dynasty_id, season) for UI initialization

    Args:
        snapshot_path: Path to snapshot .db file
        target_db_path: Path to target database
        new_dynasty_id: Optional new ID (default: auto-generate)
        new_dynasty_name: Optional new name (default: append "_DEMO")

    Returns:
        Tuple of (dynasty_id, season)
    """
    print(f"Loading snapshot: {snapshot_path}")

    # 1. Load metadata
    metadata_path = Path(snapshot_path).with_suffix('.json')
    if metadata_path.exists():
        with open(metadata_path) as f:
            metadata = json.load(f)
        original_dynasty_id = metadata['dynasty_id']
        season = metadata['season']
        print(f"  ✓ Loaded metadata:")
        print(f"    Original Dynasty: {metadata['dynasty_name']}")
        print(f"    Season: {season}, Week: {metadata.get('week', 'N/A')}")
        print(f"    Phase: {metadata.get('phase', 'N/A')}")
    else:
        # Generate metadata from database
        print("  ⚠ Metadata JSON not found, querying database...")
        conn = sqlite3.connect(snapshot_path)
        cursor = conn.execute("SELECT dynasty_id, season_year FROM dynasties LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        if not row:
            raise ValueError("No dynasties found in snapshot database")

        original_dynasty_id = row[0]
        season = row[1]
        metadata = {'dynasty_name': original_dynasty_id}

    # 2. Generate new dynasty_id
    if not new_dynasty_id:
        new_dynasty_id = f"demo_{uuid.uuid4().hex[:8]}"

    if not new_dynasty_name:
        new_dynasty_name = f"{metadata['dynasty_name']}_DEMO"

    print(f"  ✓ New Dynasty: {new_dynasty_name} ({new_dynasty_id})")

    # 3. Copy snapshot to target
    target_path = Path(target_db_path)

    if target_path.exists():
        print(f"  ⚠ Target database exists, removing...")
        target_path.unlink()

    print(f"  ✓ Copying snapshot to {target_path}...")
    shutil.copy2(snapshot_path, target_path)

    # Also copy WAL/SHM files if they exist
    for ext in ['-wal', '-shm']:
        wal_source = Path(snapshot_path).with_suffix(Path(snapshot_path).suffix + ext)
        if wal_source.exists():
            shutil.copy2(wal_source, target_path.with_suffix(target_path.suffix + ext))

    # 4. Remap dynasty_id
    remap_dynasty_id_inplace(str(target_path), original_dynasty_id, new_dynasty_id, new_dynasty_name)

    print(f"✅ Snapshot loaded successfully!")

    return (new_dynasty_id, season)


def jump_to_stage(db_path: str, dynasty_id: str, season: int, stage: StageType) -> bool:
    """
    Jump to specified offseason stage.

    Args:
        db_path: Path to database
        dynasty_id: Dynasty ID
        season: Season year
        stage: Target stage

    Returns:
        True if successful
    """
    print(f"\nJumping to stage: {stage.name}...")

    try:
        controller = StageController(db_path, dynasty_id, season)
        print(f"  Current stage: {controller.current_stage.display_name if controller.current_stage else 'None'}")

        controller.jump_to_stage(stage)

        print(f"  ✓ Jumped to {stage.name}")
        return True

    except Exception as e:
        print(f"  ❌ Failed to jump to stage: {e}")
        import traceback
        traceback.print_exc()
        return False


def launch_ui(db_path: str, dynasty_id: str, season: int, stage_name: str):
    """
    Launch Qt application with appropriate view for the stage.

    Args:
        db_path: Path to database
        dynasty_id: Dynasty ID
        season: Season year
        stage_name: Stage name (e.g., 'OFFSEASON_FREE_AGENCY')
    """
    print(f"\nLaunching UI for {stage_name}...")

    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Map stages to views
    stage_views = {
        'OFFSEASON_HONORS': ('game_cycle_ui.views.season_recap_view', 'SeasonRecapView'),
        'OFFSEASON_FRANCHISE_TAG': ('game_cycle_ui.views.franchise_tag_view', 'FranchiseTagView'),
        'OFFSEASON_RESIGNING': ('game_cycle_ui.views.resigning_view', 'ResigningView'),
        'OFFSEASON_FREE_AGENCY': ('game_cycle_ui.views.free_agency_view', 'FreeAgencyView'),
        'OFFSEASON_TRADING': ('game_cycle_ui.views.trading_view', 'TradingView'),
        'OFFSEASON_DRAFT': ('game_cycle_ui.views.draft_view', 'DraftView'),
        'OFFSEASON_ROSTER_CUTS': ('game_cycle_ui.views.roster_cuts_view', 'RosterCutsView'),
        'OFFSEASON_WAIVER_WIRE': ('game_cycle_ui.views.waiver_wire_view', 'WaiverWireView'),
        'OFFSEASON_TRAINING_CAMP': ('game_cycle_ui.views.training_camp_view', 'TrainingCampView'),
    }

    view_info = stage_views.get(stage_name)

    if view_info:
        module_path, class_name = view_info
        try:
            # Import and instantiate view
            module = __import__(module_path, fromlist=[class_name])
            view_class = getattr(module, class_name)

            # Create main window
            window = QMainWindow()
            window.setWindowTitle(f"Offseason Demo - {stage_name}")
            window.resize(1600, 1000)

            # Create and configure view
            view = view_class()
            view.set_context(dynasty_id, db_path, season)
            view.refresh_data()

            window.setCentralWidget(view)
            window.show()

            print(f"  ✓ Launched {class_name}")
            return app.exec()

        except Exception as e:
            print(f"  ⚠ Failed to load specific view: {e}")
            print(f"  Falling back to main window...")

    # Fallback - use main window
    from game_cycle_ui.main_window import GameCycleMainWindow
    try:
        main_window = GameCycleMainWindow(db_path, dynasty_id, season)
        print(f"  ✓ Launched main window")
        return app.exec()
    except Exception as e:
        print(f"  ❌ Failed to launch UI: {e}")
        import traceback
        traceback.print_exc()
        return 1


def find_latest_snapshot(snapshot_dir: Path) -> Optional[Path]:
    """
    Find the latest snapshot file in the snapshots directory.

    Args:
        snapshot_dir: Directory to search

    Returns:
        Path to latest snapshot, or None if none found
    """
    snapshots = sorted(
        snapshot_dir.glob("snapshot_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    return snapshots[0] if snapshots else None


def main():
    """Main entry point for offseason demo."""
    parser = argparse.ArgumentParser(
        description="Load snapshot and test offseason features",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Use latest snapshot, start at Honors
    python demos/offseason_demo.py

    # Jump to Free Agency
    python demos/offseason_demo.py --stage OFFSEASON_FREE_AGENCY

    # Use specific snapshot
    python demos/offseason_demo.py --snapshot demos/snapshots/snapshot_*.db

    # Force fresh load (discard existing demo)
    python demos/offseason_demo.py --fresh
        """
    )
    parser.add_argument(
        '--snapshot',
        help='Path to snapshot file (default: latest in demos/snapshots/)'
    )
    parser.add_argument(
        '--stage',
        default='OFFSEASON_HONORS',
        choices=[s.name for s in StageType if s.name.startswith('OFFSEASON_')],
        help='Offseason stage to jump to (default: OFFSEASON_HONORS)'
    )
    parser.add_argument(
        '--fresh',
        action='store_true',
        help='Force load snapshot even if demo already exists'
    )
    parser.add_argument(
        '--no-ui',
        action='store_true',
        help='Skip UI launch (just load snapshot and jump to stage)'
    )
    args = parser.parse_args()

    print("=" * 70)
    print("OFFSEASON DEMO - Rapid Offseason Testing")
    print("=" * 70)
    print()

    # Find snapshot
    snapshot_path = args.snapshot
    if not snapshot_path:
        # Use latest snapshot in demos/snapshots/
        snapshots_dir = Path(__file__).parent / "snapshots"
        snapshot = find_latest_snapshot(snapshots_dir)

        if not snapshot:
            print("❌ ERROR: No snapshots found in demos/snapshots/")
            print()
            print("Create a snapshot first with:")
            print("  PYTHONPATH=src python scripts/create_dynasty_snapshot.py --dynasty-id YOUR_DYNASTY_ID")
            print()
            return 1

        snapshot_path = str(snapshot)
        print(f"Using latest snapshot: {snapshot_path}")
        print()

    # Define target database (demo-specific to avoid polluting main DB)
    demo_db_path = str(Path(__file__).parent / "snapshots" / "offseason_demo.db")

    # Load snapshot (or use existing if --fresh not specified)
    if args.fresh or not Path(demo_db_path).exists():
        try:
            dynasty_id, season = load_snapshot_to_new_dynasty(
                snapshot_path,
                demo_db_path,
                new_dynasty_id="demo_offseason",
                new_dynasty_name="Offseason Demo"
            )
            print()
        except Exception as e:
            print(f"\n❌ ERROR loading snapshot: {e}")
            import traceback
            traceback.print_exc()
            return 1
    else:
        # Get existing dynasty info
        print(f"Using existing demo database: {demo_db_path}")
        try:
            conn = sqlite3.connect(demo_db_path)
            cursor = conn.execute("SELECT dynasty_id, season_year FROM dynasties LIMIT 1")
            row = cursor.fetchone()
            conn.close()

            if not row:
                print("❌ ERROR: No dynasties found in demo database")
                print("Run with --fresh to reload snapshot")
                return 1

            dynasty_id, season = row
            print(f"  Dynasty: {dynasty_id} (Season {season})")
            print()
        except Exception as e:
            print(f"❌ ERROR reading demo database: {e}")
            print("Run with --fresh to reload snapshot")
            return 1

    # Jump to specified offseason stage
    try:
        stage = StageType[args.stage]
        if not jump_to_stage(demo_db_path, dynasty_id, season, stage):
            print("\n⚠ Warning: Failed to jump to stage, but continuing...")
    except KeyError:
        print(f"❌ ERROR: Invalid stage '{args.stage}'")
        print(f"Valid stages: {[s.name for s in StageType if s.name.startswith('OFFSEASON_')]}")
        return 1

    # Launch UI (unless --no-ui)
    if not args.no_ui:
        return launch_ui(demo_db_path, dynasty_id, season, args.stage)
    else:
        print("\n✅ Snapshot loaded and stage set. Skipping UI (--no-ui)")
        print(f"Database: {demo_db_path}")
        print(f"Dynasty: {dynasty_id}")
        print(f"Season: {season}")
        print(f"Stage: {args.stage}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
