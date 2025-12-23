#!/usr/bin/env python3
"""
Dynasty Snapshot Creator

Creates a portable, compact snapshot of a single dynasty from the game cycle database.
Uses SQLite backup API for consistent, transactionally safe snapshots.

Features:
- Consistent snapshots even while database is in use (WAL mode compatible)
- Compact output (~45MB vs 195MB) by removing other dynasties
- Metadata JSON for snapshot tracking
- CASCADE DELETE cleanup of all dynasty-specific tables

Usage:
    # Create snapshot of current dynasty
    PYTHONPATH=src python scripts/create_dynasty_snapshot.py --dynasty-id test0927c473

    # Custom snapshot name
    PYTHONPATH=src python scripts/create_dynasty_snapshot.py --dynasty-id test0927c473 --name "playoff_ready"

    # Custom output directory
    PYTHONPATH=src python scripts/create_dynasty_snapshot.py --dynasty-id test0927c473 --output-dir path/to/snapshots
"""

import sys
import json
import sqlite3
import argparse
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any


# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))


def validate_dynasty_exists(db_path: str, dynasty_id: str) -> Dict[str, Any]:
    """
    Validate that dynasty exists in database and return its info.

    Args:
        db_path: Path to source database
        dynasty_id: Dynasty to validate

    Returns:
        Dictionary with dynasty info (dynasty_name, team_id, season_year)

    Raises:
        ValueError: If dynasty doesn't exist
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        """
        SELECT dynasty_name, team_id, season_year
        FROM dynasties
        WHERE dynasty_id = ?
        """,
        (dynasty_id,)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise ValueError(f"Dynasty '{dynasty_id}' not found in database")

    return {
        'dynasty_name': row[0],
        'team_id': row[1],
        'season_year': row[2]
    }


def get_current_week(db_path: str, dynasty_id: str) -> int:
    """
    Get current week for dynasty from dynasty_state table.

    Args:
        db_path: Path to database
        dynasty_id: Dynasty to query

    Returns:
        Current week number (defaults to 1 if not found)
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        """
        SELECT current_week
        FROM dynasty_state
        WHERE dynasty_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (dynasty_id,)
    )
    row = cursor.fetchone()
    conn.close()

    return row[0] if row else 1


def get_current_phase(db_path: str, dynasty_id: str) -> str:
    """
    Get current phase for dynasty from dynasty_state table.

    Args:
        db_path: Path to database
        dynasty_id: Dynasty to query

    Returns:
        Current phase (defaults to 'regular_season' if not found)
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        """
        SELECT current_phase
        FROM dynasty_state
        WHERE dynasty_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (dynasty_id,)
    )
    row = cursor.fetchone()
    conn.close()

    return row[0] if row else 'regular_season'


def get_game_count(db_path: str, dynasty_id: str) -> int:
    """
    Get total number of games played for this dynasty.

    Args:
        db_path: Path to database
        dynasty_id: Dynasty to query

    Returns:
        Number of games played
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        """
        SELECT COUNT(*)
        FROM games
        WHERE dynasty_id = ?
        """,
        (dynasty_id,)
    )
    count = cursor.fetchone()[0]
    conn.close()

    return count


def check_disk_space(required_mb: int = 50) -> bool:
    """
    Check if sufficient disk space is available.

    Args:
        required_mb: Required space in megabytes

    Returns:
        True if sufficient space available
    """
    import shutil as shutil_module
    stat = shutil_module.disk_usage(Path.cwd())
    available_mb = stat.free / (1024 * 1024)
    return available_mb >= required_mb


def delete_other_dynasties(conn: sqlite3.Connection, keep_dynasty_id: str) -> int:
    """
    Delete all dynasties except the one specified.

    Uses CASCADE DELETE - deleting from dynasties table automatically
    cleans up all 67 related dynasty-specific tables.

    Args:
        conn: Database connection
        keep_dynasty_id: Dynasty ID to preserve

    Returns:
        Number of dynasties deleted
    """
    # Get list of other dynasties
    cursor = conn.execute(
        """
        SELECT dynasty_id
        FROM dynasties
        WHERE dynasty_id != ?
        """,
        (keep_dynasty_id,)
    )
    other_dynasties = [row[0] for row in cursor.fetchall()]

    if not other_dynasties:
        return 0

    # Delete each dynasty (CASCADE will clean up all related tables)
    for dynasty_id in other_dynasties:
        conn.execute(
            "DELETE FROM dynasties WHERE dynasty_id = ?",
            (dynasty_id,)
        )

    conn.commit()
    return len(other_dynasties)


def create_dynasty_snapshot(
    source_db_path: str,
    snapshot_dir: str,
    dynasty_id: str,
    snapshot_name: Optional[str] = None
) -> Path:
    """
    Create a snapshot of a single dynasty using SQLite backup API.

    Process:
    1. Validate dynasty_id exists in source database
    2. Use sqlite3.Connection.backup() to create consistent copy
    3. Delete all other dynasties from snapshot (CASCADE delete)
    4. Vacuum snapshot to reclaim space (~45MB vs 195MB)
    5. Save metadata JSON (dynasty_id, season, week, timestamp)

    Args:
        source_db_path: Path to game_cycle.db
        snapshot_dir: Directory to save snapshot
        dynasty_id: Dynasty to snapshot
        snapshot_name: Optional custom name (default: auto-generated)

    Returns:
        Path to created snapshot file

    Raises:
        ValueError: If dynasty doesn't exist
        IOError: If disk space insufficient
    """
    print(f"Creating snapshot of dynasty '{dynasty_id}'...")

    # 1. Validate dynasty exists
    print("  ✓ Validating dynasty...")
    dynasty_info = validate_dynasty_exists(source_db_path, dynasty_id)
    week = get_current_week(source_db_path, dynasty_id)
    phase = get_current_phase(source_db_path, dynasty_id)
    game_count = get_game_count(source_db_path, dynasty_id)

    print(f"    Dynasty: {dynasty_info['dynasty_name']}")
    print(f"    Season: {dynasty_info['season_year']}")
    print(f"    Week: {week} ({phase})")
    print(f"    Games Played: {game_count}")

    # Check disk space
    if not check_disk_space(50):
        raise IOError("Insufficient disk space (need ~50MB)")

    # 2. Generate snapshot filename
    if not snapshot_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_name = f"snapshot_{dynasty_info['dynasty_name']}_{dynasty_info['season_year']}_w{week}_{timestamp}"

    snapshot_path = Path(snapshot_dir) / f"{snapshot_name}.db"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)

    # 3. Perform backup using SQLite backup API
    print("  ✓ Creating backup using SQLite API...")
    source_conn = sqlite3.connect(source_db_path)
    snapshot_conn = sqlite3.connect(str(snapshot_path))

    # Copy database
    with source_conn:
        source_conn.backup(snapshot_conn)

    source_conn.close()

    # 4. Clean snapshot - remove other dynasties
    print("  ✓ Removing other dynasties...")
    with snapshot_conn:
        deleted_count = delete_other_dynasties(snapshot_conn, dynasty_id)
        print(f"    Deleted {deleted_count} other dynasties")

        # Vacuum to reclaim space
        print("  ✓ Vacuuming to reclaim space...")
        snapshot_conn.execute("VACUUM")

    snapshot_conn.close()

    # 5. Save metadata
    metadata = {
        "dynasty_id": dynasty_id,
        "dynasty_name": dynasty_info['dynasty_name'],
        "team_id": dynasty_info['team_id'],
        "season": dynasty_info['season_year'],
        "week": week,
        "phase": phase,
        "games_played": game_count,
        "created_at": datetime.now().isoformat(),
        "source_db": str(source_db_path),
        "snapshot_size_mb": round(snapshot_path.stat().st_size / (1024 * 1024), 2)
    }

    metadata_path = snapshot_path.with_suffix('.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"\n✅ Snapshot created successfully!")
    print(f"   Database: {snapshot_path}")
    print(f"   Metadata: {metadata_path}")
    print(f"   Size: {metadata['snapshot_size_mb']} MB")

    return snapshot_path


def main():
    """Main entry point for snapshot creator."""
    parser = argparse.ArgumentParser(
        description="Create a snapshot of a single dynasty from game cycle database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Create snapshot of current dynasty
    PYTHONPATH=src python scripts/create_dynasty_snapshot.py --dynasty-id test0927c473

    # Custom snapshot name
    PYTHONPATH=src python scripts/create_dynasty_snapshot.py --dynasty-id test0927c473 --name "playoff_ready"

    # Custom output directory
    PYTHONPATH=src python scripts/create_dynasty_snapshot.py --dynasty-id test0927c473 --output-dir path/to/snapshots
        """
    )
    parser.add_argument(
        '--dynasty-id',
        required=True,
        help='Dynasty ID to snapshot (e.g., test0927c473)'
    )
    parser.add_argument(
        '--name',
        help='Custom snapshot name (default: auto-generated with timestamp)'
    )
    parser.add_argument(
        '--output-dir',
        default=str(project_root / "demos" / "snapshots"),
        help='Output directory for snapshot (default: demos/snapshots/)'
    )
    parser.add_argument(
        '--source-db',
        default=str(project_root / "data" / "database" / "game_cycle" / "game_cycle.db"),
        help='Source database path (default: data/database/game_cycle/game_cycle.db)'
    )
    args = parser.parse_args()

    print("=" * 70)
    print("DYNASTY SNAPSHOT CREATOR")
    print("=" * 70)
    print()

    try:
        snapshot_path = create_dynasty_snapshot(
            source_db_path=args.source_db,
            snapshot_dir=args.output_dir,
            dynasty_id=args.dynasty_id,
            snapshot_name=args.name
        )
        print()
        print("Next steps:")
        print("  1. Load snapshot with: python demos/offseason_demo.py")
        print(f"  2. Or specify: python demos/offseason_demo.py --snapshot {snapshot_path}")
        print()
        return 0

    except ValueError as e:
        print(f"\n❌ ERROR: {e}")
        return 1
    except IOError as e:
        print(f"\n❌ ERROR: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
