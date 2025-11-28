"""
Transaction API for querying player transaction history.

Provides comprehensive query methods for retrieving and analyzing
all player transactions (drafts, signings, releases, trades, roster moves)
with dynasty isolation and flexible filtering.
"""

from typing import Dict, List, Any, Optional
from datetime import date
import json
import sqlite3
import logging
from pathlib import Path
from database.connection import DatabaseConnection


class TransactionAPI:
    """
    API for querying player transaction history.

    Provides methods for retrieving transaction data across multiple
    dimensions: player, team, time, transaction type, and aggregations.

    All queries are dynasty-aware to ensure proper data isolation.

    Example:
        >>> api = TransactionAPI('data/database/nfl_simulation.db')
        >>> transactions = api.get_team_transactions(
        ...     team_id=7,
        ...     dynasty_id='my_dynasty',
        ...     season=2025
        ... )
    """

    def __init__(self, database_path: str = "data/database/nfl_simulation.db"):
        """
        Initialize Transaction API.

        Args:
            database_path: Path to SQLite database
        """
        self.database_path = database_path
        self.logger = logging.getLogger(__name__)
        self.db_connection = DatabaseConnection(database_path)

        # Ensure schema exists before any queries
        self._ensure_schema_exists()

    def _ensure_schema_exists(self) -> None:
        """Ensure player_transactions table exists."""
        migration_path = Path(__file__).parent.parent / "database" / "migrations" / "003_player_transactions_table.sql"

        if not migration_path.exists():
            self.logger.warning(f"Migration file not found: {migration_path}")
            return

        try:
            with sqlite3.connect(self.database_path, timeout=30.0) as conn:
                conn.execute("PRAGMA foreign_keys = ON")

                # Check if table exists
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='player_transactions'"
                )
                if cursor.fetchone() is None:
                    # Run migration
                    with open(migration_path, 'r') as f:
                        migration_sql = f.read()
                    conn.executescript(migration_sql)
                    conn.commit()
                    self.logger.info("Player transactions schema initialized successfully")
        except Exception as e:
            self.logger.error(f"Error ensuring schema exists: {e}")
            raise

    def get_player_transactions(
        self,
        player_id: int,
        dynasty_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all transactions for a specific player.

        Returns complete transaction history for a player across
        all teams and seasons within a dynasty.

        Args:
            player_id: Player ID
            dynasty_id: Dynasty identifier

        Returns:
            List of transaction dicts sorted by date (newest first)

        Example:
            >>> api = TransactionAPI()
            >>> transactions = api.get_player_transactions(
            ...     player_id=12345,
            ...     dynasty_id='my_dynasty'
            ... )
            >>> for txn in transactions:
            ...     print(f"{txn['transaction_date']}: {txn['transaction_type']}")
        """
        query = '''
            SELECT
                pt.id AS transaction_id,
                pt.dynasty_id,
                pt.season,
                pt.transaction_type,
                pt.player_id,
                COALESCE(pt.first_name || ' ' || pt.last_name, '') AS player_name,
                pt.position,
                pt.from_team_id,
                pt.to_team_id,
                pt.transaction_date,
                pt.details,
                pt.contract_id,
                pt.event_id,
                pt.created_at
            FROM player_transactions pt
            WHERE pt.player_id = ?
                AND pt.dynasty_id = ?
            ORDER BY pt.transaction_date DESC, pt.created_at DESC
        '''

        results = self.db_connection.execute_query(query, (player_id, dynasty_id))
        return [self._parse_transaction_row(row) for row in results]

    def get_team_transactions(
        self,
        team_id: int,
        dynasty_id: str,
        season: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all transactions for a specific team.

        Returns transactions where the team was either the source (from_team_id)
        or destination (to_team_id).

        Args:
            team_id: Team ID (1-32)
            dynasty_id: Dynasty identifier
            season: Optional season filter

        Returns:
            List of transaction dicts sorted by date (newest first)

        Example:
            >>> api = TransactionAPI()
            >>> # Get all transactions for team 7 in 2025
            >>> transactions = api.get_team_transactions(
            ...     team_id=7,
            ...     dynasty_id='my_dynasty',
            ...     season=2025
            ... )
        """
        if season is not None:
            query = '''
                SELECT
                    pt.id AS transaction_id,
                    pt.dynasty_id,
                    pt.season,
                    pt.transaction_type,
                    pt.player_id,
                    COALESCE(pt.first_name || ' ' || pt.last_name, '') AS player_name,
                    pt.position,
                    pt.from_team_id,
                    pt.to_team_id,
                    pt.transaction_date,
                    pt.details,
                    pt.contract_id,
                    pt.event_id,
                    pt.created_at
                FROM player_transactions pt
                WHERE pt.dynasty_id = ?
                    AND pt.season = ?
                    AND (pt.from_team_id = ? OR pt.to_team_id = ?)
                ORDER BY pt.transaction_date DESC, pt.created_at DESC
            '''
            params = (dynasty_id, season, team_id, team_id)
        else:
            query = '''
                SELECT
                    pt.id AS transaction_id,
                    pt.dynasty_id,
                    pt.season,
                    pt.transaction_type,
                    pt.player_id,
                    COALESCE(pt.first_name || ' ' || pt.last_name, '') AS player_name,
                    pt.position,
                    pt.from_team_id,
                    pt.to_team_id,
                    pt.transaction_date,
                    pt.details,
                    pt.contract_id,
                    pt.event_id,
                    pt.created_at
                FROM player_transactions pt
                WHERE pt.dynasty_id = ?
                    AND (pt.from_team_id = ? OR pt.to_team_id = ?)
                ORDER BY pt.transaction_date DESC, pt.created_at DESC
            '''
            params = (dynasty_id, team_id, team_id)

        results = self.db_connection.execute_query(query, params)
        return [self._parse_transaction_row(row) for row in results]

    def get_recent_transactions(
        self,
        dynasty_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get most recent transactions across entire league.

        Useful for displaying league-wide transaction feeds.

        Args:
            dynasty_id: Dynasty identifier
            limit: Maximum number of transactions to return (default 50)

        Returns:
            List of transaction dicts sorted by date (newest first)

        Example:
            >>> api = TransactionAPI()
            >>> # Get last 25 transactions
            >>> recent = api.get_recent_transactions(
            ...     dynasty_id='my_dynasty',
            ...     limit=25
            ... )
        """
        query = '''
            SELECT
                pt.id AS transaction_id,
                pt.dynasty_id,
                pt.season,
                pt.transaction_type,
                pt.player_id,
                COALESCE(pt.first_name || ' ' || pt.last_name, '') AS player_name,
                pt.position,
                pt.from_team_id,
                pt.to_team_id,
                pt.transaction_date,
                pt.details,
                pt.contract_id,
                pt.event_id,
                pt.created_at
            FROM player_transactions pt
            WHERE pt.dynasty_id = ?
            ORDER BY pt.transaction_date DESC, pt.created_at DESC
            LIMIT ?
        '''

        results = self.db_connection.execute_query(query, (dynasty_id, limit))
        return [self._parse_transaction_row(row) for row in results]

    def get_transactions_by_type(
        self,
        transaction_type: str,
        dynasty_id: str,
        season: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all transactions of a specific type.

        Args:
            transaction_type: Transaction type (DRAFT, UFA_SIGNING, RELEASE, etc.)
            dynasty_id: Dynasty identifier
            season: Optional season filter
            limit: Optional maximum number of transactions to return

        Returns:
            List of transaction dicts sorted by date (newest first)

        Example:
            >>> api = TransactionAPI()
            >>> # Get all draft picks in 2025
            >>> drafts = api.get_transactions_by_type(
            ...     transaction_type='DRAFT',
            ...     dynasty_id='my_dynasty',
            ...     season=2025
            ... )
        """
        if season is not None:
            query = '''
                SELECT
                    pt.id AS transaction_id,
                    pt.dynasty_id,
                    pt.season,
                    pt.transaction_type,
                    pt.player_id,
                    COALESCE(pt.first_name || ' ' || pt.last_name, '') AS player_name,
                    pt.position,
                    pt.from_team_id,
                    pt.to_team_id,
                    pt.transaction_date,
                    pt.details,
                    pt.contract_id,
                    pt.event_id,
                    pt.created_at
                FROM player_transactions pt
                WHERE pt.transaction_type = ?
                    AND pt.dynasty_id = ?
                    AND pt.season = ?
                ORDER BY pt.transaction_date DESC, pt.created_at DESC
            '''
            params = [transaction_type, dynasty_id, season]
        else:
            query = '''
                SELECT
                    pt.id AS transaction_id,
                    pt.dynasty_id,
                    pt.season,
                    pt.transaction_type,
                    pt.player_id,
                    COALESCE(pt.first_name || ' ' || pt.last_name, '') AS player_name,
                    pt.position,
                    pt.from_team_id,
                    pt.to_team_id,
                    pt.transaction_date,
                    pt.details,
                    pt.contract_id,
                    pt.event_id,
                    pt.created_at
                FROM player_transactions pt
                WHERE pt.transaction_type = ?
                    AND pt.dynasty_id = ?
                ORDER BY pt.transaction_date DESC, pt.created_at DESC
            '''
            params = [transaction_type, dynasty_id]

        # Add limit clause if specified
        if limit is not None:
            query += ' LIMIT ?'
            params.append(limit)

        results = self.db_connection.execute_query(query, tuple(params))
        return [self._parse_transaction_row(row) for row in results]

    def get_transactions_by_date_range(
        self,
        dynasty_id: str,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """
        Get all transactions within a date range.

        Useful for analyzing specific periods (e.g., free agency window,
        training camp, trade deadline).

        Args:
            dynasty_id: Dynasty identifier
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            List of transaction dicts sorted by date (newest first)

        Example:
            >>> api = TransactionAPI()
            >>> from datetime import date
            >>> # Get all transactions during March 2025 free agency
            >>> transactions = api.get_transactions_by_date_range(
            ...     dynasty_id='my_dynasty',
            ...     start_date=date(2025, 3, 1),
            ...     end_date=date(2025, 3, 31)
            ... )
        """
        query = '''
            SELECT
                pt.id AS transaction_id,
                pt.dynasty_id,
                pt.season,
                pt.transaction_type,
                pt.player_id,
                COALESCE(pt.first_name || ' ' || pt.last_name, '') AS player_name,
                pt.position,
                pt.from_team_id,
                pt.to_team_id,
                pt.transaction_date,
                pt.details,
                pt.contract_id,
                pt.event_id,
                pt.created_at
            FROM player_transactions pt
            WHERE pt.dynasty_id = ?
                AND pt.transaction_date >= ?
                AND pt.transaction_date <= ?
            ORDER BY pt.transaction_date DESC, pt.created_at DESC
        '''

        results = self.db_connection.execute_query(
            query,
            (dynasty_id, start_date.isoformat(), end_date.isoformat())
        )
        return [self._parse_transaction_row(row) for row in results]

    def get_transaction_count_by_team(
        self,
        dynasty_id: str,
        season: int
    ) -> Dict[int, Dict[str, int]]:
        """
        Get transaction count by team for analytics.

        Returns a breakdown of how many transactions each team made,
        split by transaction type.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Dict mapping team_id -> {transaction_type: count}

        Example:
            >>> api = TransactionAPI()
            >>> counts = api.get_transaction_count_by_team(
            ...     dynasty_id='my_dynasty',
            ...     season=2025
            ... )
            >>> print(f"Team 7 made {counts[7]['total']} transactions")
        """
        query = '''
            SELECT
                COALESCE(pt.to_team_id, pt.from_team_id) as team_id,
                pt.transaction_type,
                COUNT(*) as count
            FROM player_transactions pt
            WHERE pt.dynasty_id = ?
                AND pt.season = ?
                AND (pt.to_team_id IS NOT NULL OR pt.from_team_id IS NOT NULL)
            GROUP BY team_id, pt.transaction_type
        '''

        results = self.db_connection.execute_query(query, (dynasty_id, season))

        # Build nested dict: team_id -> {type: count, total: count}
        team_counts = {}
        for row in results:
            team_id = row['team_id']
            txn_type = row['transaction_type']
            count = row['count']

            if team_id not in team_counts:
                team_counts[team_id] = {'total': 0}

            team_counts[team_id][txn_type] = count
            team_counts[team_id]['total'] += count

        return team_counts

    def get_transaction_summary(
        self,
        dynasty_id: str,
        season: int
    ) -> Dict[str, Any]:
        """
        Get season-level transaction summary statistics.

        Provides aggregated counts and analytics for a season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Dict with summary statistics:
            - total_transactions: Total count
            - by_type: {transaction_type: count}
            - most_active_team: Team ID with most transactions

        Example:
            >>> api = TransactionAPI()
            >>> summary = api.get_transaction_summary(
            ...     dynasty_id='my_dynasty',
            ...     season=2025
            ... )
            >>> print(f"Total transactions: {summary['total_transactions']}")
        """
        # Get total count
        total_query = '''
            SELECT COUNT(*) as total
            FROM player_transactions pt
            WHERE pt.dynasty_id = ? AND pt.season = ?
        '''
        total_result = self.db_connection.execute_query(total_query, (dynasty_id, season))
        total_transactions = total_result[0]['total'] if total_result else 0

        # Get count by type
        type_query = '''
            SELECT
                pt.transaction_type,
                COUNT(*) as count
            FROM player_transactions pt
            WHERE pt.dynasty_id = ? AND pt.season = ?
            GROUP BY pt.transaction_type
        '''
        type_results = self.db_connection.execute_query(type_query, (dynasty_id, season))
        by_type = {row['transaction_type']: row['count'] for row in type_results}

        # Get most active team
        team_counts = self.get_transaction_count_by_team(dynasty_id, season)
        most_active_team = max(team_counts.items(), key=lambda x: x[1]['total'])[0] if team_counts else None

        return {
            'total_transactions': total_transactions,
            'by_type': by_type,
            'most_active_team': most_active_team,
            'team_counts': team_counts
        }

    def _parse_transaction_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse database row into transaction dict.

        Handles JSON parsing for details field.

        Args:
            row: Database row dict

        Returns:
            Parsed transaction dict
        """
        parsed = dict(row)

        # Parse details JSON field if present
        if 'details' in parsed and parsed['details']:
            try:
                parsed['details'] = json.loads(parsed['details'])
            except (json.JSONDecodeError, TypeError):
                # Keep as string if parsing fails
                pass

        return parsed
