"""
Transaction Context Module

Provides a context manager for atomic multi-operation database transactions.
Ensures ACID properties with automatic commit/rollback handling.

Usage:
    Basic transaction:
        with TransactionContext(conn) as tx:
            cursor.execute("INSERT INTO players ...")
            cursor.execute("UPDATE contracts ...")
            # Auto-commits on success, auto-rolls back on exception

    Explicit commit:
        with TransactionContext(conn) as tx:
            cursor.execute("INSERT ...")
            tx.commit()  # Explicit commit
            cursor.execute("INSERT ...")
            # Final commit still happens on context exit

    Nested transactions (savepoints):
        with TransactionContext(conn) as tx:
            cursor.execute("INSERT ...")
            with TransactionContext(conn) as nested_tx:
                cursor.execute("UPDATE ...")
                # Nested transaction uses savepoint
            # Continues outer transaction

    Transaction modes:
        # Immediate locking (for write operations)
        with TransactionContext(conn, mode="IMMEDIATE") as tx:
            cursor.execute("UPDATE ...")

        # Deferred locking (read-only, default)
        with TransactionContext(conn, mode="DEFERRED") as tx:
            cursor.execute("SELECT ...")

        # Exclusive locking (for critical sections)
        with TransactionContext(conn, mode="EXCLUSIVE") as tx:
            cursor.execute("DELETE ...")
"""

import sqlite3
import logging
from typing import Optional, Literal
from enum import Enum


class TransactionState(Enum):
    """Transaction lifecycle states."""
    INACTIVE = "inactive"
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"


TransactionMode = Literal["DEFERRED", "IMMEDIATE", "EXCLUSIVE"]


class TransactionContext:
    """
    Context manager for atomic database transactions.

    Features:
    - Automatic BEGIN on enter, COMMIT on success, ROLLBACK on exception
    - Support for nested transactions using savepoints
    - Multiple transaction modes (DEFERRED, IMMEDIATE, EXCLUSIVE)
    - Transaction state tracking and validation
    - Detailed logging for debugging
    - Connection validation before operations

    Attributes:
        connection: SQLite database connection
        mode: Transaction isolation mode
        state: Current transaction state
        savepoint_name: Name for nested transaction savepoint (if nested)
        is_nested: Whether this is a nested transaction (savepoint)
    """

    # Class-level counter for nested transactions
    _savepoint_counter = 0

    def __init__(
        self,
        connection: sqlite3.Connection,
        mode: TransactionMode = "DEFERRED"
    ):
        """
        Initialize transaction context.

        Args:
            connection: Active SQLite connection
            mode: Transaction mode (DEFERRED, IMMEDIATE, EXCLUSIVE)
                - DEFERRED (default): Lock acquired on first write operation
                - IMMEDIATE: Lock acquired immediately (prevents write conflicts)
                - EXCLUSIVE: Exclusive lock acquired immediately (blocks all other connections)

        Raises:
            ValueError: If connection is None or invalid mode
            TypeError: If connection is not a sqlite3.Connection
        """
        if connection is None:
            raise ValueError("Connection cannot be None")

        if not isinstance(connection, sqlite3.Connection):
            raise TypeError(f"Expected sqlite3.Connection, got {type(connection)}")

        if mode not in ("DEFERRED", "IMMEDIATE", "EXCLUSIVE"):
            raise ValueError(f"Invalid transaction mode: {mode}. Must be DEFERRED, IMMEDIATE, or EXCLUSIVE")

        self.connection = connection
        self.mode = mode
        self.state = TransactionState.INACTIVE
        self.savepoint_name: Optional[str] = None
        self.is_nested = False
        self.logger = logging.getLogger(__name__)

        # Track if we're in a nested transaction
        self._check_if_nested()

    def _check_if_nested(self) -> None:
        """Check if we're entering a nested transaction (savepoint)."""
        try:
            # Check if a transaction is already active
            # SQLite's in_transaction property tells us if we're in a transaction
            if self.connection.in_transaction:
                self.is_nested = True
                TransactionContext._savepoint_counter += 1
                self.savepoint_name = f"savepoint_{TransactionContext._savepoint_counter}"
                self.logger.debug(f"Detected nested transaction, will use savepoint: {self.savepoint_name}")
        except AttributeError:
            # Python < 3.2 doesn't have in_transaction, assume not nested
            self.is_nested = False

    def __enter__(self) -> "TransactionContext":
        """
        Enter transaction context.

        Begins a new transaction or creates a savepoint for nested transactions.

        Returns:
            Self for use in context manager

        Raises:
            sqlite3.OperationalError: If unable to begin transaction
        """
        try:
            if self.is_nested:
                # Use savepoint for nested transaction
                self.logger.debug(f"Creating savepoint: {self.savepoint_name}")
                self.connection.execute(f"SAVEPOINT {self.savepoint_name}")
            else:
                # Begin new transaction with specified mode
                self.logger.debug(f"Beginning {self.mode} transaction")
                self.connection.execute(f"BEGIN {self.mode}")

            self.state = TransactionState.ACTIVE
            return self

        except sqlite3.OperationalError as e:
            self.logger.error(f"Failed to begin transaction: {e}")
            self.state = TransactionState.INACTIVE
            raise

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """
        Exit transaction context.

        Commits on success, rolls back on exception.

        Args:
            exc_type: Exception type (if exception occurred)
            exc_val: Exception value (if exception occurred)
            exc_tb: Exception traceback (if exception occurred)

        Returns:
            False to propagate exceptions
        """
        if self.state != TransactionState.ACTIVE:
            # Transaction already committed or rolled back
            self.logger.debug(f"Transaction already {self.state.value}, skipping auto-action")
            return False

        try:
            if exc_type is None:
                # No exception, commit transaction
                self._commit_internal()
            else:
                # Exception occurred, rollback transaction
                self.logger.warning(
                    f"Exception in transaction context: {exc_type.__name__}: {exc_val}. Rolling back."
                )
                self._rollback_internal()
        except Exception as e:
            # Error during commit/rollback
            self.logger.error(f"Error during transaction cleanup: {e}")
            try:
                # Attempt emergency rollback
                self._rollback_internal()
            except Exception as rollback_error:
                self.logger.critical(f"Emergency rollback failed: {rollback_error}")

        # Always propagate exceptions
        return False

    def _commit_internal(self) -> None:
        """Internal commit implementation."""
        if self.state == TransactionState.COMMITTED:
            self.logger.warning("Transaction already committed, skipping")
            return

        try:
            if self.is_nested:
                # Release savepoint (commits nested transaction)
                self.logger.debug(f"Releasing savepoint: {self.savepoint_name}")
                self.connection.execute(f"RELEASE {self.savepoint_name}")
            else:
                # Commit top-level transaction
                self.logger.debug("Committing transaction")
                self.connection.commit()

            self.state = TransactionState.COMMITTED
            self.logger.debug("Transaction committed successfully")

        except sqlite3.OperationalError as e:
            self.logger.error(f"Commit failed: {e}")
            self.state = TransactionState.ACTIVE
            raise

    def _rollback_internal(self) -> None:
        """Internal rollback implementation."""
        if self.state == TransactionState.ROLLED_BACK:
            self.logger.warning("Transaction already rolled back, skipping")
            return

        try:
            if self.is_nested:
                # Rollback to savepoint
                self.logger.debug(f"Rolling back to savepoint: {self.savepoint_name}")
                self.connection.execute(f"ROLLBACK TO {self.savepoint_name}")
                # Note: ROLLBACK TO keeps the savepoint, so we need to release it
                self.connection.execute(f"RELEASE {self.savepoint_name}")
            else:
                # Rollback top-level transaction
                self.logger.debug("Rolling back transaction")
                self.connection.rollback()

            self.state = TransactionState.ROLLED_BACK
            self.logger.debug("Transaction rolled back successfully")

        except sqlite3.OperationalError as e:
            self.logger.error(f"Rollback failed: {e}")
            raise

    def commit(self) -> None:
        """
        Explicitly commit the transaction.

        Useful for committing at a specific point within the context.
        Note: Transaction will still auto-commit on context exit if not already committed.

        Raises:
            sqlite3.OperationalError: If commit fails
            RuntimeError: If transaction is not active
        """
        if self.state != TransactionState.ACTIVE:
            raise RuntimeError(f"Cannot commit transaction in state: {self.state.value}")

        self._commit_internal()

    def rollback(self) -> None:
        """
        Explicitly rollback the transaction.

        Useful for rolling back at a specific point within the context.

        Raises:
            sqlite3.OperationalError: If rollback fails
            RuntimeError: If transaction is not active
        """
        if self.state != TransactionState.ACTIVE:
            raise RuntimeError(f"Cannot rollback transaction in state: {self.state.value}")

        self._rollback_internal()

    @property
    def is_active(self) -> bool:
        """Check if transaction is currently active."""
        return self.state == TransactionState.ACTIVE

    @property
    def is_committed(self) -> bool:
        """Check if transaction has been committed."""
        return self.state == TransactionState.COMMITTED

    @property
    def is_rolled_back(self) -> bool:
        """Check if transaction has been rolled back."""
        return self.state == TransactionState.ROLLED_BACK

    def __repr__(self) -> str:
        """String representation of transaction context."""
        nested_info = f", savepoint={self.savepoint_name}" if self.is_nested else ""
        return f"TransactionContext(mode={self.mode}, state={self.state.value}{nested_info})"


# Convenience function for creating transaction contexts
def transaction(
    connection: sqlite3.Connection,
    mode: TransactionMode = "DEFERRED"
) -> TransactionContext:
    """
    Create a transaction context.

    Convenience function for creating TransactionContext instances.

    Args:
        connection: SQLite database connection
        mode: Transaction mode (DEFERRED, IMMEDIATE, EXCLUSIVE)

    Returns:
        TransactionContext ready for use in with statement

    Example:
        with transaction(conn, mode="IMMEDIATE") as tx:
            cursor.execute("INSERT ...")
            cursor.execute("UPDATE ...")
    """
    return TransactionContext(connection, mode)
