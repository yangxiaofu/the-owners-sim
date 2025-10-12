"""
Verify Duplicates

SQL queries to check for duplicate playoff game events in the database.
"""

import sqlite3
from typing import Dict, List, Any, Tuple
from pathlib import Path


class DuplicateChecker:
    """Check for duplicate playoff games in database."""

    def __init__(self, db_path: str):
        """
        Initialize checker.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path

    def check_all(self, dynasty_id: str, season: int) -> Dict[str, Any]:
        """
        Run all duplicate checks.

        Args:
            dynasty_id: Dynasty to check
            season: Season year

        Returns:
            Dictionary with check results
        """
        results = {
            'duplicates': self.find_duplicate_game_ids(dynasty_id),
            'total_playoff_games': self.count_playoff_games(dynasty_id, season),
            'games_by_round': self.count_games_by_round(dynasty_id, season),
            'all_playoff_events': self.list_all_playoff_events(dynasty_id, season)
        }

        return results

    def find_duplicate_game_ids(self, dynasty_id: str) -> List[Dict[str, Any]]:
        """
        Find game_ids that appear more than once.

        Args:
            dynasty_id: Dynasty to check

        Returns:
            List of duplicate game_ids with counts
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT game_id, COUNT(*) as count
                FROM events
                WHERE dynasty_id = ?
                  AND game_id LIKE 'playoff_%'
                GROUP BY game_id
                HAVING COUNT(*) > 1
                ORDER BY count DESC, game_id
            ''', (dynasty_id,))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        finally:
            conn.close()

    def count_playoff_games(self, dynasty_id: str, season: int) -> int:
        """
        Count total playoff game events.

        Args:
            dynasty_id: Dynasty to check
            season: Season year

        Returns:
            Total count of playoff events
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM events
                WHERE dynasty_id = ?
                  AND game_id LIKE 'playoff_' || ? || '_%'
            ''', (dynasty_id, season))

            return cursor.fetchone()[0]

        finally:
            conn.close()

    def count_games_by_round(self, dynasty_id: str, season: int) -> Dict[str, int]:
        """
        Count playoff games by round.

        Args:
            dynasty_id: Dynasty to check
            season: Season year

        Returns:
            Dict mapping round name -> count
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT
                    CASE
                        WHEN game_id LIKE '%_wild_card_%' THEN 'wild_card'
                        WHEN game_id LIKE '%_divisional_%' THEN 'divisional'
                        WHEN game_id LIKE '%_conference_%' THEN 'conference'
                        WHEN game_id LIKE '%_super_bowl_%' THEN 'super_bowl'
                        ELSE 'unknown'
                    END as round,
                    COUNT(*) as count
                FROM events
                WHERE dynasty_id = ?
                  AND game_id LIKE 'playoff_' || ? || '_%'
                GROUP BY round
                ORDER BY round
            ''', (dynasty_id, season))

            rows = cursor.fetchall()
            return {row['round']: row['count'] for row in rows}

        finally:
            conn.close()

    def list_all_playoff_events(self, dynasty_id: str, season: int) -> List[Dict[str, Any]]:
        """
        List all playoff events with details.

        Args:
            dynasty_id: Dynasty to check
            season: Season year

        Returns:
            List of event details
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT event_id, game_id, event_type, timestamp
                FROM events
                WHERE dynasty_id = ?
                  AND game_id LIKE 'playoff_%'
                ORDER BY game_id, timestamp
            ''', (dynasty_id,))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        finally:
            conn.close()

    def print_report(self, dynasty_id: str, season: int):
        """
        Print a comprehensive duplicate check report.

        Args:
            dynasty_id: Dynasty to check
            season: Season year
        """
        results = self.check_all(dynasty_id, season)

        print("\n" + "="*80)
        print("PLAYOFF DUPLICATE CHECK REPORT".center(80))
        print("="*80)
        print(f"Dynasty: {dynasty_id}")
        print(f"Season: {season}")
        print("="*80)

        # Check for duplicates
        duplicates = results['duplicates']
        if duplicates:
            print(f"\n❌ DUPLICATES FOUND: {len(duplicates)} game_id(s) appear multiple times")
            for dup in duplicates:
                print(f"   {dup['game_id']}: {dup['count']} occurrences")
        else:
            print("\n✅ NO DUPLICATES: All game_ids are unique")

        # Total games
        total = results['total_playoff_games']
        print(f"\nTotal Playoff Events: {total}")

        # Games by round
        print("\nGames by Round:")
        games_by_round = results['games_by_round']
        expected_counts = {
            'wild_card': 6,
            'divisional': 4,
            'conference': 2,
            'super_bowl': 1
        }

        for round_name, expected in expected_counts.items():
            actual = games_by_round.get(round_name, 0)
            status = "✅" if actual == expected else "❌"
            print(f"  {status} {round_name:12s}: {actual:2d} (expected {expected})")

        # All events (if verbose needed)
        if False:  # Set to True for detailed listing
            print("\nAll Playoff Events:")
            for event in results['all_playoff_events']:
                print(f"  {event['event_id'][:8]}... | {event['game_id']}")

        print("="*80)


def main():
    """Test the duplicate checker."""
    import sys

    if len(sys.argv) < 3:
        print("Usage: python verify_duplicates.py <database_path> <dynasty_id> [season]")
        print("\nExample:")
        print("  python verify_duplicates.py :memory: test_dynasty 2024")
        sys.exit(1)

    db_path = sys.argv[1]
    dynasty_id = sys.argv[2]
    season = int(sys.argv[3]) if len(sys.argv) > 3 else 2024

    checker = DuplicateChecker(db_path)
    checker.print_report(dynasty_id, season)


if __name__ == "__main__":
    main()
