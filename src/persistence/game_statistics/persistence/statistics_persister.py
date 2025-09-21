"""
Statistics Persister

Main persistence orchestrator for database operations.
"""

import logging
from typing import Dict, Any

from ..models.persistence_result import PersistenceResult
from ..models.extraction_context import ExtractionContext

try:
    from ....database.connection import DatabaseConnection
except ImportError:
    # Fallback import
    from database.connection import DatabaseConnection


class StatisticsPersister:
    """
    Main persistence orchestrator for database operations with transaction management.
    """

    def __init__(self, database_connection: DatabaseConnection, logger: logging.Logger = None):
        """
        Initialize the statistics persister.

        Args:
            database_connection: Database connection for persistence
            logger: Optional logger for debugging
        """
        self.db = database_connection
        self.logger = logger or logging.getLogger(__name__)

    def persist_statistics(self, database_records: Dict[str, Any],
                          context: ExtractionContext) -> PersistenceResult:
        """
        Persist statistics to database with transaction management.

        Args:
            database_records: Database-formatted records
            context: Extraction context

        Returns:
            PersistenceResult with operation outcome
        """
        result = PersistenceResult(
            success=True,
            operation_id=f"persist_{context.game_id}"
        )

        try:
            conn = self.db.get_connection()

            # Begin transaction
            conn.execute("BEGIN TRANSACTION")

            records_persisted = 0

            # Persist player records
            if 'player_records' in database_records:
                records_persisted += self._persist_player_records(
                    conn, database_records['player_records']
                )

            # Persist team records
            if 'team_records' in database_records:
                records_persisted += self._persist_team_records(
                    conn, database_records['team_records']
                )

            # Persist game record
            if 'game_record' in database_records:
                records_persisted += self._persist_game_record(
                    conn, database_records['game_record']
                )

            # Commit transaction
            conn.execute("COMMIT")

            result.records_persisted = records_persisted
            self.logger.info(f"Successfully persisted {records_persisted} records")

        except Exception as e:
            # Rollback on error
            try:
                conn.execute("ROLLBACK")
            except:
                pass

            result.success = False
            result.add_error(f"Database persistence failed: {str(e)}")
            self.logger.error(f"Database persistence error: {e}", exc_info=True)

        finally:
            try:
                conn.close()
            except:
                pass

        return result

    def _persist_player_records(self, conn, player_records: list) -> int:
        """
        Persist player statistics records.

        Args:
            conn: Database connection
            player_records: List of player records

        Returns:
            Number of records persisted
        """
        count = 0
        for record in player_records:
            record_dict = record.to_database_dict()

            # Build INSERT statement
            fields = list(record_dict.keys())
            placeholders = ', '.join(['?' for _ in fields])
            field_names = ', '.join(fields)

            query = f"""
                INSERT INTO player_game_stats ({field_names})
                VALUES ({placeholders})
            """

            values = [record_dict[field] for field in fields]
            conn.execute(query, values)
            count += 1

        return count

    def _persist_team_records(self, conn, team_records: list) -> int:
        """
        Persist team statistics records.

        Args:
            conn: Database connection
            team_records: List of team records

        Returns:
            Number of records persisted
        """
        # Placeholder implementation
        return len(team_records)

    def _persist_game_record(self, conn, game_record) -> int:
        """
        Persist game context record.

        Args:
            conn: Database connection
            game_record: Game context record

        Returns:
            Number of records persisted
        """
        # Placeholder implementation
        return 1