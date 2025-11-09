"""
Database Checkpoint Manager

This module provides transaction checkpoint management using SQLite savepoints.
Enables atomic multi-operation sequences with rollback capability for complex
database operations like playoff round scheduling and calendar advancement.

Key Features:
- Named savepoints with metadata tracking
- Nested checkpoint support via SQLite savepoints
- Checkpoint lifecycle management (create, commit, rollback)
- Rich metadata for debugging and audit trails
- Integration with TransactionContext for atomic operations

Usage Example:
    with TransactionContext(conn, mode="IMMEDIATE") as tx:
        checkpoint_mgr = CheckpointManager(conn, tx)

        # Create checkpoint before risky operation
        checkpoint_id = checkpoint_mgr.create_checkpoint(
            name="schedule_divisional_round",
            operation="playoff_scheduling",
            description="Scheduling divisional round games",
            metadata={"round": "divisional", "season": 2025}
        )

        try:
            # Perform database operations
            schedule_divisional_round()

            # Commit checkpoint on success
            checkpoint_mgr.commit_checkpoint(checkpoint_id)
        except Exception as e:
            # Rollback to checkpoint on failure
            checkpoint_mgr.rollback_to_checkpoint(checkpoint_id)
            raise
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import sqlite3
import logging


@dataclass
class CheckpointInfo:
    """
    Metadata for a database checkpoint.

    Attributes:
        name: Unique checkpoint identifier
        savepoint_name: SQLite savepoint name (generated from name)
        operation: Operation type (e.g., "playoff_scheduling", "calendar_advancement")
        created_at: Timestamp when checkpoint was created
        description: Human-readable description of checkpoint
        is_active: Whether checkpoint is still active (not committed/rolled back)
        metadata: Additional context (dynasty_id, season, round, etc.)
    """
    name: str
    savepoint_name: str
    operation: str
    created_at: datetime
    description: Optional[str] = None
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert checkpoint info to dictionary for serialization"""
        return {
            "name": self.name,
            "savepoint_name": self.savepoint_name,
            "operation": self.operation,
            "created_at": self.created_at.isoformat(),
            "description": self.description,
            "is_active": self.is_active,
            "metadata": self.metadata
        }


class CheckpointManager:
    """
    Manager for named database checkpoints using SQLite savepoints.

    This class provides a high-level interface for creating, committing, and
    rolling back database checkpoints. It integrates with TransactionContext
    to enable nested transaction support and atomic multi-operation sequences.

    Savepoint Naming Convention:
    - User-friendly names: "schedule_divisional_round", "advance_to_week_2"
    - SQLite savepoint names: "sp_schedule_divisional_round", "sp_advance_to_week_2"

    Attributes:
        _connection: SQLite database connection
        _transaction_context: Active TransactionContext instance
        _checkpoints: Registry of active checkpoints by name
        _checkpoint_stack: Stack of checkpoint names (for nested checkpoints)
        _logger: Logger for checkpoint operations
    """

    def __init__(
        self,
        connection: sqlite3.Connection,
        transaction_context: Optional[Any] = None
    ):
        """
        Initialize checkpoint manager.

        Args:
            connection: SQLite database connection
            transaction_context: Optional TransactionContext instance for validation
        """
        self._connection = connection
        self._transaction_context = transaction_context
        self._checkpoints: Dict[str, CheckpointInfo] = {}
        self._checkpoint_stack: List[str] = []
        self._logger = logging.getLogger(__name__)

    def create_checkpoint(
        self,
        name: str,
        operation: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a named checkpoint using SQLite savepoint.

        Creates a savepoint in the database that can be rolled back to if
        subsequent operations fail. Supports nested checkpoints via SQLite's
        savepoint mechanism.

        Args:
            name: Unique checkpoint identifier (user-friendly)
            operation: Operation type (e.g., "playoff_scheduling")
            description: Human-readable description
            metadata: Additional context (dynasty_id, season, round, etc.)

        Returns:
            Checkpoint name (same as input name parameter)

        Raises:
            ValueError: If checkpoint with same name already exists
            sqlite3.Error: If savepoint creation fails

        Example:
            >>> mgr = CheckpointManager(conn)
            >>> checkpoint_id = mgr.create_checkpoint(
            ...     name="schedule_round",
            ...     operation="playoff_scheduling",
            ...     metadata={"round": "divisional"}
            ... )
        """
        if name in self._checkpoints:
            raise ValueError(
                f"Checkpoint '{name}' already exists. "
                f"Use a unique name or commit/rollback existing checkpoint first."
            )

        # Generate SQLite savepoint name (prefix with "sp_")
        savepoint_name = f"sp_{name}"

        # Create checkpoint info
        checkpoint_info = CheckpointInfo(
            name=name,
            savepoint_name=savepoint_name,
            operation=operation,
            created_at=datetime.now(),
            description=description,
            metadata=metadata or {}
        )

        # Execute SAVEPOINT SQL
        try:
            cursor = self._connection.cursor()
            cursor.execute(f"SAVEPOINT {savepoint_name}")

            # Register checkpoint
            self._checkpoints[name] = checkpoint_info
            self._checkpoint_stack.append(name)

            self._logger.debug(
                f"Created checkpoint '{name}' (savepoint: {savepoint_name}) "
                f"for operation '{operation}'"
            )

            return name

        except sqlite3.Error as e:
            self._logger.error(
                f"Failed to create checkpoint '{name}': {e}"
            )
            raise

    def rollback_to_checkpoint(self, name: str) -> bool:
        """
        Rollback to a specific checkpoint.

        Rolls back all database changes made since the checkpoint was created.
        This releases the savepoint and all nested savepoints created after it.

        Args:
            name: Checkpoint name to rollback to

        Returns:
            True if rollback successful, False if checkpoint not found

        Raises:
            sqlite3.Error: If rollback fails

        Example:
            >>> try:
            ...     schedule_playoff_round()
            ... except Exception:
            ...     mgr.rollback_to_checkpoint("schedule_round")
        """
        if name not in self._checkpoints:
            self._logger.warning(
                f"Cannot rollback: Checkpoint '{name}' not found"
            )
            return False

        checkpoint_info = self._checkpoints[name]

        if not checkpoint_info.is_active:
            self._logger.warning(
                f"Cannot rollback: Checkpoint '{name}' is not active "
                f"(already committed or rolled back)"
            )
            return False

        savepoint_name = checkpoint_info.savepoint_name

        try:
            # Execute ROLLBACK TO SAVEPOINT
            cursor = self._connection.cursor()
            cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")

            # Mark checkpoint as inactive
            checkpoint_info.is_active = False

            # Remove checkpoint and all nested checkpoints from stack
            if name in self._checkpoint_stack:
                index = self._checkpoint_stack.index(name)
                removed_checkpoints = self._checkpoint_stack[index:]
                self._checkpoint_stack = self._checkpoint_stack[:index]

                # Mark all removed checkpoints as inactive
                for cp_name in removed_checkpoints:
                    if cp_name in self._checkpoints:
                        self._checkpoints[cp_name].is_active = False

            self._logger.info(
                f"Rolled back to checkpoint '{name}' "
                f"(operation: {checkpoint_info.operation})"
            )

            return True

        except sqlite3.Error as e:
            self._logger.error(
                f"Failed to rollback to checkpoint '{name}': {e}"
            )
            raise

    def commit_checkpoint(self, name: str) -> bool:
        """
        Commit a checkpoint (release savepoint).

        Releases the savepoint, making all changes since checkpoint creation
        permanent (within the current transaction). The checkpoint cannot be
        rolled back after committing.

        Args:
            name: Checkpoint name to commit

        Returns:
            True if commit successful, False if checkpoint not found

        Raises:
            sqlite3.Error: If savepoint release fails

        Example:
            >>> schedule_playoff_round()
            >>> mgr.commit_checkpoint("schedule_round")  # Changes are now permanent
        """
        if name not in self._checkpoints:
            self._logger.warning(
                f"Cannot commit: Checkpoint '{name}' not found"
            )
            return False

        checkpoint_info = self._checkpoints[name]

        if not checkpoint_info.is_active:
            self._logger.warning(
                f"Cannot commit: Checkpoint '{name}' is not active "
                f"(already committed or rolled back)"
            )
            return False

        savepoint_name = checkpoint_info.savepoint_name

        try:
            # Execute RELEASE SAVEPOINT
            cursor = self._connection.cursor()
            cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")

            # Mark checkpoint as inactive
            checkpoint_info.is_active = False

            # Remove from stack
            if name in self._checkpoint_stack:
                self._checkpoint_stack.remove(name)

            self._logger.debug(
                f"Committed checkpoint '{name}' "
                f"(operation: {checkpoint_info.operation})"
            )

            return True

        except sqlite3.Error as e:
            self._logger.error(
                f"Failed to commit checkpoint '{name}': {e}"
            )
            raise

    def list_checkpoints(self, active_only: bool = True) -> List[str]:
        """
        List checkpoint names.

        Args:
            active_only: If True, only return active checkpoints

        Returns:
            List of checkpoint names

        Example:
            >>> mgr.list_checkpoints()
            ['schedule_divisional', 'schedule_conference']
            >>> mgr.list_checkpoints(active_only=False)
            ['schedule_wildcard', 'schedule_divisional', 'schedule_conference']
        """
        if active_only:
            return [
                name for name, info in self._checkpoints.items()
                if info.is_active
            ]
        else:
            return list(self._checkpoints.keys())

    def get_checkpoint_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get checkpoint metadata.

        Args:
            name: Checkpoint name

        Returns:
            Checkpoint metadata dictionary, or None if not found

        Example:
            >>> info = mgr.get_checkpoint_info("schedule_round")
            >>> print(info["operation"])
            'playoff_scheduling'
            >>> print(info["metadata"]["round"])
            'divisional'
        """
        if name not in self._checkpoints:
            return None

        return self._checkpoints[name].to_dict()

    def clear_inactive_checkpoints(self) -> int:
        """
        Remove inactive checkpoints from registry.

        Cleans up committed or rolled back checkpoints to free memory.
        Active checkpoints are not affected.

        Returns:
            Number of checkpoints removed

        Example:
            >>> count = mgr.clear_inactive_checkpoints()
            >>> print(f"Removed {count} inactive checkpoints")
        """
        inactive_names = [
            name for name, info in self._checkpoints.items()
            if not info.is_active
        ]

        for name in inactive_names:
            del self._checkpoints[name]

        if inactive_names:
            self._logger.debug(
                f"Cleared {len(inactive_names)} inactive checkpoints"
            )

        return len(inactive_names)


# Example usage
if __name__ == "__main__":
    import sys
    from pathlib import Path

    # Add src to path for imports
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from database.transaction_context import TransactionContext

    print("=" * 80)
    print("Checkpoint Manager Examples")
    print("=" * 80)

    # Example 1: Basic checkpoint usage
    print("\n1. Basic Checkpoint Usage:")

    # Create in-memory database
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE test_data (id INTEGER PRIMARY KEY, value TEXT)")

    with TransactionContext(conn, mode="IMMEDIATE") as tx:
        checkpoint_mgr = CheckpointManager(conn, tx)

        # Create checkpoint
        checkpoint_id = checkpoint_mgr.create_checkpoint(
            name="insert_data",
            operation="data_insertion",
            description="Inserting test data",
            metadata={"table": "test_data", "count": 3}
        )
        print(f"Created checkpoint: {checkpoint_id}")

        # Insert some data
        conn.execute("INSERT INTO test_data (value) VALUES ('row1')")
        conn.execute("INSERT INTO test_data (value) VALUES ('row2')")

        # Check data
        cursor = conn.execute("SELECT COUNT(*) FROM test_data")
        count = cursor.fetchone()[0]
        print(f"Rows after insert: {count}")

        # Rollback checkpoint
        checkpoint_mgr.rollback_to_checkpoint(checkpoint_id)
        print("Rolled back checkpoint")

        # Check data again
        cursor = conn.execute("SELECT COUNT(*) FROM test_data")
        count = cursor.fetchone()[0]
        print(f"Rows after rollback: {count}")

    # Example 2: Nested checkpoints
    print("\n" + "=" * 80)
    print("\n2. Nested Checkpoints:")

    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE games (id INTEGER PRIMARY KEY, round TEXT)")

    with TransactionContext(conn, mode="IMMEDIATE") as tx:
        checkpoint_mgr = CheckpointManager(conn, tx)

        # Outer checkpoint
        outer_cp = checkpoint_mgr.create_checkpoint(
            name="schedule_all_rounds",
            operation="playoff_scheduling",
            description="Schedule all playoff rounds"
        )
        print(f"Created outer checkpoint: {outer_cp}")

        # Schedule Wild Card (with nested checkpoint)
        wildcard_cp = checkpoint_mgr.create_checkpoint(
            name="schedule_wildcard",
            operation="playoff_scheduling",
            metadata={"round": "wild_card"}
        )
        print(f"  Created nested checkpoint: {wildcard_cp}")

        conn.execute("INSERT INTO games (round) VALUES ('wild_card')")
        conn.execute("INSERT INTO games (round) VALUES ('wild_card')")

        checkpoint_mgr.commit_checkpoint(wildcard_cp)
        print(f"  Committed {wildcard_cp}")

        # Schedule Divisional (with nested checkpoint)
        divisional_cp = checkpoint_mgr.create_checkpoint(
            name="schedule_divisional",
            operation="playoff_scheduling",
            metadata={"round": "divisional"}
        )
        print(f"  Created nested checkpoint: {divisional_cp}")

        conn.execute("INSERT INTO games (round) VALUES ('divisional')")

        # Simulate failure - rollback divisional only
        print(f"  Simulating failure, rolling back {divisional_cp}")
        checkpoint_mgr.rollback_to_checkpoint(divisional_cp)

        # Commit outer checkpoint
        checkpoint_mgr.commit_checkpoint(outer_cp)
        print(f"Committed {outer_cp}")

        # Check final data
        cursor = conn.execute("SELECT round, COUNT(*) FROM games GROUP BY round")
        print("\nFinal game counts:")
        for round_name, count in cursor.fetchall():
            print(f"  {round_name}: {count}")

    # Example 3: Checkpoint metadata
    print("\n" + "=" * 80)
    print("\n3. Checkpoint Metadata:")

    conn = sqlite3.connect(":memory:")

    with TransactionContext(conn, mode="IMMEDIATE") as tx:
        checkpoint_mgr = CheckpointManager(conn, tx)

        # Create checkpoint with rich metadata
        cp_name = checkpoint_mgr.create_checkpoint(
            name="advance_calendar",
            operation="calendar_advancement",
            description="Advance calendar from Week 10 to Week 11",
            metadata={
                "dynasty_id": "test_dynasty",
                "season": 2025,
                "from_week": 10,
                "to_week": 11,
                "phase": "regular_season"
            }
        )

        # Get checkpoint info
        info = checkpoint_mgr.get_checkpoint_info(cp_name)
        print(f"Checkpoint Info:")
        print(f"  Name: {info['name']}")
        print(f"  Operation: {info['operation']}")
        print(f"  Description: {info['description']}")
        print(f"  Created: {info['created_at']}")
        print(f"  Is Active: {info['is_active']}")
        print(f"  Metadata:")
        for key, value in info['metadata'].items():
            print(f"    {key}: {value}")

        # List all checkpoints
        print(f"\nActive checkpoints: {checkpoint_mgr.list_checkpoints()}")

        # Commit and clean up
        checkpoint_mgr.commit_checkpoint(cp_name)
        print(f"\nAfter commit:")
        print(f"  Active checkpoints: {checkpoint_mgr.list_checkpoints()}")
        print(f"  All checkpoints: {checkpoint_mgr.list_checkpoints(active_only=False)}")

        # Clear inactive
        count = checkpoint_mgr.clear_inactive_checkpoints()
        print(f"\nCleared {count} inactive checkpoints")
        print(f"  All checkpoints: {checkpoint_mgr.list_checkpoints(active_only=False)}")

    conn.close()

    print("\n" + "=" * 80)
    print("\nAll checkpoint manager examples completed successfully!")
