#!/usr/bin/env python3
"""
Migration script to add performance indices to existing databases.

This script adds indices that improve query performance for statistics queries.
It is safe to run multiple times (idempotent) due to IF NOT EXISTS clauses.

Usage:
    python scripts/migrate_add_indices.py [--db-path PATH]

If no path provided, migrates both default databases:
    - data/database/game_cycle/game_cycle.db
    - data/database/nfl_simulation.db
"""

import argparse
import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Indices to add for player_game_stats
PLAYER_GAME_STATS_INDICES = [
    ("idx_player_stats_team_game", "player_game_stats", "(dynasty_id, team_id, game_id)"),
    ("idx_player_stats_team", "player_game_stats", "(dynasty_id, team_id)"),
    ("idx_player_stats_season_type", "player_game_stats", "(dynasty_id, season_type)"),
]

# Indices to add for player_game_grades
PLAYER_GAME_GRADES_INDICES = [
    ("idx_game_grades_game", "player_game_grades", "(dynasty_id, game_id)"),
]

# Indices to add for box_scores
BOX_SCORES_INDICES = [
    ("idx_box_scores_team", "box_scores", "(dynasty_id, team_id)"),
    ("idx_box_scores_game_team", "box_scores", "(dynasty_id, game_id, team_id)"),
]

ALL_INDICES = (
    PLAYER_GAME_STATS_INDICES
    + PLAYER_GAME_GRADES_INDICES
    + BOX_SCORES_INDICES
)


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    """Check if a table exists in the database."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None


def index_exists(conn: sqlite3.Connection, index_name: str) -> bool:
    """Check if an index exists in the database."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
        (index_name,)
    )
    return cursor.fetchone() is not None


def add_indices(db_path: str, dry_run: bool = False) -> dict:
    """
    Add performance indices to an existing database.

    Args:
        db_path: Path to the SQLite database
        dry_run: If True, only report what would be done without making changes

    Returns:
        Dictionary with counts of indices created, skipped, and errors
    """
    results = {
        "created": 0,
        "skipped": 0,
        "table_missing": 0,
        "errors": [],
    }

    path = Path(db_path)
    if not path.exists():
        logger.warning(f"Database not found: {db_path}")
        results["errors"].append(f"Database not found: {db_path}")
        return results

    logger.info(f"Processing database: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        for index_name, table_name, columns in ALL_INDICES:
            # Check if table exists
            if not table_exists(conn, table_name):
                logger.info(f"  Table '{table_name}' not found, skipping {index_name}")
                results["table_missing"] += 1
                continue

            # Check if index already exists
            if index_exists(conn, index_name):
                logger.info(f"  Index '{index_name}' already exists, skipping")
                results["skipped"] += 1
                continue

            # Create the index
            sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}{columns}"
            if dry_run:
                logger.info(f"  [DRY RUN] Would create: {sql}")
                results["created"] += 1
            else:
                try:
                    conn.execute(sql)
                    conn.commit()
                    logger.info(f"  Created index: {index_name}")
                    results["created"] += 1
                except sqlite3.Error as e:
                    error_msg = f"Failed to create {index_name}: {e}"
                    logger.error(f"  {error_msg}")
                    results["errors"].append(error_msg)

        conn.close()

    except sqlite3.Error as e:
        error_msg = f"Database connection error: {e}"
        logger.error(error_msg)
        results["errors"].append(error_msg)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Add performance indices to existing databases"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        help="Path to specific database to migrate (default: migrate both standard databases)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    args = parser.parse_args()

    if args.db_path:
        databases = [args.db_path]
    else:
        # Default to both standard databases
        project_root = Path(__file__).parent.parent
        databases = [
            str(project_root / "data" / "database" / "game_cycle" / "game_cycle.db"),
            str(project_root / "data" / "database" / "nfl_simulation.db"),
        ]

    total_results = {"created": 0, "skipped": 0, "table_missing": 0, "errors": []}

    for db_path in databases:
        results = add_indices(db_path, dry_run=args.dry_run)
        total_results["created"] += results["created"]
        total_results["skipped"] += results["skipped"]
        total_results["table_missing"] += results["table_missing"]
        total_results["errors"].extend(results["errors"])

    # Summary
    print("\n" + "=" * 50)
    print("Migration Summary")
    print("=" * 50)
    print(f"Indices created:        {total_results['created']}")
    print(f"Indices already exist:  {total_results['skipped']}")
    print(f"Tables not found:       {total_results['table_missing']}")
    print(f"Errors:                 {len(total_results['errors'])}")

    if total_results["errors"]:
        print("\nErrors encountered:")
        for error in total_results["errors"]:
            print(f"  - {error}")

    return 0 if not total_results["errors"] else 1


if __name__ == "__main__":
    exit(main())