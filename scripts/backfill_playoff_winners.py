#!/usr/bin/env python3
"""
Backfill Missing Playoff Game Winners

This script fixes missing winner_id and winner_name data for playoff games.
All playoff games in dynasty 'test1' (season 2025) have complete score data
but null winner_id/winner_name in the events table, which blocks draft order calculation.

Usage:
    # Show what would be updated (dry-run mode, default)
    python scripts/backfill_playoff_winners.py

    # Actually update the database
    python scripts/backfill_playoff_winners.py --execute

Requirements:
    - Database: data/database/nfl_simulation.db
    - Dynasty: test1
    - Season: 2025
"""

import sqlite3
import json
import argparse
import sys
import os
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from team_management.teams.team_loader import TeamDataLoader
from database.transaction_context import TransactionContext


class PlayoffWinnersBackfiller:
    """Backfills missing winner_id and winner_name for playoff games"""

    def __init__(self, db_path: str, dynasty_id: str = "test1", season: int = 2025):
        """
        Initialize the backfiller

        Args:
            db_path: Path to SQLite database
            dynasty_id: Dynasty identifier (default: test1)
            season: Season year (default: 2025)
        """
        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self.season = season
        self.team_loader = TeamDataLoader()
        self.updated_games = []
        self.errors = []

    def get_playoff_games(self) -> list:
        """
        Query events table for playoff games with missing winner_id

        Returns:
            List of event dictionaries with playoff game data
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Query for playoff games with score data but null winner_id
            query = '''
                SELECT
                    event_id,
                    data,
                    timestamp
                FROM events
                WHERE dynasty_id = ?
                  AND event_type = 'GAME'
                  AND json_extract(data, '$.parameters.season') = ?
                  AND json_extract(data, '$.parameters.season_type') = 'playoffs'
                  AND json_extract(data, '$.results.winner_id') IS NULL
                ORDER BY timestamp ASC
            '''

            cursor.execute(query, (self.dynasty_id, self.season))
            rows = cursor.fetchall()

            games = []
            for row in rows:
                try:
                    event_data = json.loads(row['data'])
                    games.append({
                        'event_id': row['event_id'],
                        'data': event_data,
                        'timestamp': row['timestamp']
                    })
                except json.JSONDecodeError as e:
                    self.errors.append(f"Invalid JSON for event {row['event_id']}: {e}")

            return games

        finally:
            conn.close()

    def calculate_winner(self, away_score: int, home_score: int,
                        away_team_id: int, home_team_id: int) -> tuple:
        """
        Calculate winner from scores

        Args:
            away_score: Away team score
            home_score: Home team score
            away_team_id: Away team ID
            home_team_id: Home team ID

        Returns:
            Tuple of (winner_id, winner_name)
        """
        if away_score > home_score:
            winner_id = away_team_id
        elif home_score > away_score:
            winner_id = home_team_id
        else:
            # Tie? This shouldn't happen in playoffs, but handle it
            self.errors.append(f"Tie score detected: {away_team_id} {away_score}-{home_score} {home_team_id}")
            return None, None

        # Get team name
        try:
            team = self.team_loader.get_team_by_id(winner_id)
            winner_name = team.full_name if team else f"Team {winner_id}"
        except Exception as e:
            self.errors.append(f"Error loading team {winner_id}: {e}")
            winner_name = f"Team {winner_id}"

        return winner_id, winner_name

    def backfill_winners(self, dry_run: bool = True) -> dict:
        """
        Backfill winner data for all playoff games

        Args:
            dry_run: If True, don't actually update database (default: True)

        Returns:
            Dictionary with results:
            {
                'total_games': int,
                'updated_count': int,
                'errors': list,
                'updated_games': list
            }
        """
        print(f"\n{'='*80}")
        print(f"PLAYOFF WINNERS BACKFILL - {'DRY RUN' if dry_run else 'EXECUTE'}")
        print(f"{'='*80}")
        print(f"Database: {self.db_path}")
        print(f"Dynasty: {self.dynasty_id}")
        print(f"Season: {self.season}")
        print()

        # Get all playoff games with missing winners
        games = self.get_playoff_games()
        print(f"Found {len(games)} playoff game(s) with missing winner data\n")

        if not games:
            print("No games to update!")
            return {
                'total_games': 0,
                'updated_count': 0,
                'errors': self.errors,
                'updated_games': []
            }

        # Process each game
        for idx, game in enumerate(games, 1):
            try:
                event_id = game['event_id']
                data = game['data']

                params = data.get('parameters', {})
                results = data.get('results', {})

                # Extract scores and team IDs
                away_team_id = params.get('away_team_id')
                home_team_id = params.get('home_team_id')
                away_score = results.get('away_score')
                home_score = results.get('home_score')
                game_type = params.get('game_type', 'unknown')

                if away_team_id is None or home_team_id is None:
                    self.errors.append(f"Event {event_id}: Missing team IDs")
                    continue

                if away_score is None or home_score is None:
                    self.errors.append(f"Event {event_id}: Missing score data")
                    continue

                # Calculate winner
                winner_id, winner_name = self.calculate_winner(
                    away_score, home_score, away_team_id, home_team_id
                )

                if winner_id is None:
                    continue

                # Get team names for display
                try:
                    away_team = self.team_loader.get_team_by_id(away_team_id)
                    home_team = self.team_loader.get_team_by_id(home_team_id)
                    away_name = away_team.full_name if away_team else f"Team {away_team_id}"
                    home_name = home_team.full_name if home_team else f"Team {home_team_id}"
                except Exception as e:
                    away_name = f"Team {away_team_id}"
                    home_name = f"Team {home_team_id}"

                # Print game info
                print(f"{idx}. {game_type.upper()}")
                print(f"   {away_name} ({away_team_id}) {away_score}")
                print(f"   {home_name} ({home_team_id}) {home_score}")
                print(f"   → Winner: {winner_name} (ID: {winner_id})")
                print()

                self.updated_games.append({
                    'event_id': event_id,
                    'away_team_id': away_team_id,
                    'home_team_id': home_team_id,
                    'away_score': away_score,
                    'home_score': home_score,
                    'winner_id': winner_id,
                    'winner_name': winner_name,
                    'game_type': game_type,
                    'old_data': data.copy()
                })

            except Exception as e:
                self.errors.append(f"Error processing event {game['event_id']}: {e}")

        # Update database if not dry-run
        if not dry_run and self.updated_games:
            self._execute_updates()

        # Print summary
        self._print_summary(dry_run)

        return {
            'total_games': len(games),
            'updated_count': len(self.updated_games),
            'errors': self.errors,
            'updated_games': self.updated_games
        }

    def _execute_updates(self) -> None:
        """Execute database updates with transaction safety"""
        conn = sqlite3.connect(self.db_path)

        try:
            cursor = conn.cursor()
            updated_count = 0

            for game in self.updated_games:
                event_id = game['event_id']
                winner_id = game['winner_id']
                winner_name = game['winner_name']
                old_data = game['old_data']

                # Update the JSON data with winner info
                new_data = old_data.copy()
                new_data['results']['winner_id'] = winner_id
                new_data['results']['winner_name'] = winner_name

                # Update event in database
                cursor.execute('''
                    UPDATE events
                    SET data = ?
                    WHERE event_id = ?
                ''', (json.dumps(new_data), event_id))

                updated_count += cursor.rowcount

            conn.commit()

            print(f"\n{'✓'} Successfully updated {updated_count} game(s) in database")

        except Exception as e:
            conn.rollback()
            raise Exception(f"Database update failed: {e}")
        finally:
            conn.close()

    def _print_summary(self, dry_run: bool) -> None:
        """Print execution summary"""
        print(f"{'='*80}")
        print(f"SUMMARY")
        print(f"{'='*80}")
        print(f"Games processed: {len(self.updated_games)}")

        if self.errors:
            print(f"Errors encountered: {len(self.errors)}")
            for error in self.errors:
                print(f"  - {error}")

        if dry_run:
            print(f"\n[DRY RUN MODE] No changes made to database")
            print(f"Run with --execute flag to apply updates")
        else:
            print(f"\n[EXECUTE MODE] All updates applied")

        print(f"{'='*80}\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Backfill missing winner data for playoff games",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show what would be updated (dry-run, default)
  python scripts/backfill_playoff_winners.py

  # Actually update the database
  python scripts/backfill_playoff_winners.py --execute

  # Custom dynasty and season
  python scripts/backfill_playoff_winners.py --execute --dynasty custom_dynasty --season 2026
        """
    )

    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually execute the updates (default: dry-run mode)'
    )
    parser.add_argument(
        '--dynasty',
        default='test1',
        help='Dynasty ID (default: test1)'
    )
    parser.add_argument(
        '--season',
        type=int,
        default=2025,
        help='Season year (default: 2025)'
    )
    parser.add_argument(
        '--database',
        default='data/database/nfl_simulation.db',
        help='Path to database (default: data/database/nfl_simulation.db)'
    )

    args = parser.parse_args()

    # Ensure database exists
    if not os.path.exists(args.database):
        print(f"Error: Database not found at {args.database}")
        sys.exit(1)

    # Run backfill
    backfiller = PlayoffWinnersBackfiller(
        db_path=args.database,
        dynasty_id=args.dynasty,
        season=args.season
    )

    result = backfiller.backfill_winners(dry_run=not args.execute)

    # Exit with error code if there were errors
    if result['errors']:
        sys.exit(1)

    if result['updated_count'] == 0:
        sys.exit(0)

    sys.exit(0)


if __name__ == '__main__':
    main()
