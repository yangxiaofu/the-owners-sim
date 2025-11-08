"""
Database Connection Pool

Provides thread-safe connection pooling for SQLite database access across the application.
This module implements a fixed-size connection pool with automatic recycling, configuration
management, and comprehensive error handling.

Key Features:
- Thread-safe connection acquisition and release
- Configurable pool size (default: 5 connections)
- Automatic connection validation before reuse
- WAL mode and foreign key enforcement
- Connection timeout handling
- Graceful cleanup on pool destruction

Usage:
    pool = ConnectionPool("data/database/nfl_simulation.db")
    conn = pool.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM teams")
        # ... use connection ...
    finally:
        pool.return_connection(conn)

    # Cleanup when done
    pool.close_all()

Thread Safety:
    All public methods are thread-safe and can be called from multiple threads
    concurrently. The pool uses internal locking to prevent race conditions.
"""

import logging
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PoolStats:
    """Statistics for connection pool monitoring."""

    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    connection_requests: int = 0
    connection_reuses: int = 0
    connection_creations: int = 0
    validation_failures: int = 0
    wait_time_total: float = 0.0


class ConnectionPool:
    """
    Thread-safe SQLite connection pool with automatic recycling.

    This class manages a pool of SQLite connections to minimize connection
    overhead and provide thread-safe database access. Connections are
    automatically configured with WAL mode, foreign keys, and row factories.

    Attributes:
        database_path: Path to the SQLite database file
        max_connections: Maximum number of connections in the pool
        timeout: Connection timeout in seconds

    Example:
        >>> pool = ConnectionPool("test.db", max_connections=3)
        >>> conn = pool.get_connection()
        >>> cursor = conn.cursor()
        >>> cursor.execute("SELECT 1")
        >>> pool.return_connection(conn)
        >>> pool.close_all()
    """

    def __init__(
        self,
        database_path: str,
        max_connections: int = 5,
        timeout: float = 30.0
    ):
        """
        Initialize the connection pool.

        Args:
            database_path: Path to the SQLite database file (or ":memory:")
            max_connections: Maximum number of connections to maintain
            timeout: Connection timeout in seconds

        Raises:
            ValueError: If max_connections < 1 or timeout <= 0
        """
        if max_connections < 1:
            raise ValueError("max_connections must be at least 1")
        if timeout <= 0:
            raise ValueError("timeout must be positive")

        self.database_path = database_path
        self.max_connections = max_connections
        self.timeout = timeout

        # Connection tracking
        self._idle_connections: list[sqlite3.Connection] = []
        self._active_connections: set[sqlite3.Connection] = set()
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)

        # Statistics tracking
        self._stats = PoolStats()

        # Shutdown flag
        self._closed = False

        logger.info(
            f"Initialized connection pool: path={database_path}, "
            f"max_connections={max_connections}, timeout={timeout}s"
        )

    def get_connection(self) -> sqlite3.Connection:
        """
        Acquire a connection from the pool.

        This method will return an idle connection if available, create a new
        connection if the pool is not full, or block until a connection becomes
        available. All returned connections are validated before use.

        Returns:
            A configured SQLite connection ready for use

        Raises:
            RuntimeError: If the pool has been closed
            sqlite3.Error: If connection creation or configuration fails
            TimeoutError: If no connection becomes available within timeout period

        Thread Safety:
            This method is thread-safe and can be called from multiple threads.
        """
        start_time = time.time()

        with self._condition:
            if self._closed:
                raise RuntimeError("Connection pool has been closed")

            self._stats.connection_requests += 1

            while True:
                # Try to reuse an idle connection
                if self._idle_connections:
                    conn = self._idle_connections.pop()

                    # Validate connection before reuse
                    if self._validate_connection(conn):
                        self._active_connections.add(conn)
                        self._stats.active_connections = len(self._active_connections)
                        self._stats.idle_connections = len(self._idle_connections)
                        self._stats.connection_reuses += 1

                        wait_time = time.time() - start_time
                        self._stats.wait_time_total += wait_time

                        logger.debug(
                            f"Reused connection from pool (active={len(self._active_connections)}, "
                            f"idle={len(self._idle_connections)}, wait={wait_time:.3f}s)"
                        )
                        return conn
                    else:
                        # Connection failed validation, discard it
                        self._stats.validation_failures += 1
                        logger.warning("Discarded invalid connection from pool")
                        try:
                            conn.close()
                        except Exception as e:
                            logger.error(f"Error closing invalid connection: {e}")
                        continue

                # Create new connection if pool not full
                total_connections = len(self._active_connections) + len(self._idle_connections)
                if total_connections < self.max_connections:
                    try:
                        conn = self._create_connection()
                        self._active_connections.add(conn)
                        self._stats.total_connections = total_connections + 1
                        self._stats.active_connections = len(self._active_connections)
                        self._stats.connection_creations += 1

                        wait_time = time.time() - start_time
                        self._stats.wait_time_total += wait_time

                        logger.debug(
                            f"Created new connection (total={self._stats.total_connections}, "
                            f"active={len(self._active_connections)}, wait={wait_time:.3f}s)"
                        )
                        return conn
                    except sqlite3.Error as e:
                        logger.error(f"Failed to create database connection: {e}")
                        raise

                # Pool is full, wait for a connection to be returned
                elapsed = time.time() - start_time
                remaining = self.timeout - elapsed

                if remaining <= 0:
                    logger.error(
                        f"Connection timeout after {elapsed:.2f}s "
                        f"(active={len(self._active_connections)}, "
                        f"idle={len(self._idle_connections)})"
                    )
                    raise TimeoutError(
                        f"Failed to acquire connection within {self.timeout}s timeout. "
                        f"Pool exhausted with {len(self._active_connections)} active connections."
                    )

                logger.debug(
                    f"Waiting for available connection (remaining={remaining:.2f}s, "
                    f"active={len(self._active_connections)}, idle={len(self._idle_connections)})"
                )

                # Wait for connection to be returned (with timeout)
                self._condition.wait(timeout=remaining)

                if self._closed:
                    raise RuntimeError("Connection pool closed while waiting")

    def return_connection(self, conn: sqlite3.Connection) -> None:
        """
        Return a connection to the pool for reuse.

        The connection is validated before being returned to the idle pool.
        Invalid connections are discarded and closed.

        Args:
            conn: The connection to return to the pool

        Raises:
            ValueError: If the connection was not acquired from this pool

        Thread Safety:
            This method is thread-safe and can be called from multiple threads.
        """
        with self._condition:
            if self._closed:
                # Pool is closed, just close the connection
                try:
                    conn.close()
                except Exception as e:
                    logger.error(f"Error closing connection during shutdown: {e}")
                return

            if conn not in self._active_connections:
                raise ValueError("Connection was not acquired from this pool")

            self._active_connections.remove(conn)

            # Validate connection before returning to pool
            if self._validate_connection(conn):
                self._idle_connections.append(conn)
                self._stats.active_connections = len(self._active_connections)
                self._stats.idle_connections = len(self._idle_connections)

                logger.debug(
                    f"Returned connection to pool (active={len(self._active_connections)}, "
                    f"idle={len(self._idle_connections)})"
                )
            else:
                # Connection is invalid, discard it
                self._stats.validation_failures += 1
                self._stats.total_connections -= 1
                logger.warning("Discarded invalid connection on return")
                try:
                    conn.close()
                except Exception as e:
                    logger.error(f"Error closing invalid connection: {e}")

            # Notify waiting threads
            self._condition.notify()

    def close_all(self) -> None:
        """
        Close all connections and shut down the pool.

        This method marks the pool as closed, preventing new connection requests,
        and closes all active and idle connections. Any threads waiting for
        connections will be notified.

        After calling this method, the pool cannot be reused. Create a new
        ConnectionPool instance if needed.

        Thread Safety:
            This method is thread-safe and can be called from multiple threads,
            but should typically only be called once during shutdown.
        """
        with self._condition:
            if self._closed:
                logger.warning("Connection pool already closed")
                return

            self._closed = True

            # Close all idle connections
            while self._idle_connections:
                conn = self._idle_connections.pop()
                try:
                    conn.close()
                except Exception as e:
                    logger.error(f"Error closing idle connection: {e}")

            # Close all active connections (should be empty in normal shutdown)
            if self._active_connections:
                logger.warning(
                    f"Closing pool with {len(self._active_connections)} active connections"
                )
                for conn in list(self._active_connections):
                    try:
                        conn.close()
                    except Exception as e:
                        logger.error(f"Error closing active connection: {e}")
                self._active_connections.clear()

            # Wake up any waiting threads
            self._condition.notify_all()

            logger.info(
                f"Closed connection pool (requests={self._stats.connection_requests}, "
                f"creations={self._stats.connection_creations}, "
                f"reuses={self._stats.connection_reuses}, "
                f"validation_failures={self._stats.validation_failures}, "
                f"avg_wait={self._stats.wait_time_total / max(self._stats.connection_requests, 1):.3f}s)"
            )

    def get_stats(self) -> PoolStats:
        """
        Get current pool statistics.

        Returns:
            PoolStats object with current pool metrics

        Thread Safety:
            This method is thread-safe but returns a snapshot that may be
            outdated by the time it's examined.
        """
        with self._lock:
            # Create a copy to avoid race conditions
            stats = PoolStats(
                total_connections=self._stats.total_connections,
                active_connections=len(self._active_connections),
                idle_connections=len(self._idle_connections),
                connection_requests=self._stats.connection_requests,
                connection_reuses=self._stats.connection_reuses,
                connection_creations=self._stats.connection_creations,
                validation_failures=self._stats.validation_failures,
                wait_time_total=self._stats.wait_time_total
            )
        return stats

    def _create_connection(self) -> sqlite3.Connection:
        """
        Create and configure a new database connection.

        Returns:
            A configured SQLite connection

        Raises:
            sqlite3.Error: If connection creation or configuration fails
        """
        try:
            # Create connection with timeout
            conn = sqlite3.connect(
                self.database_path,
                timeout=self.timeout,
                check_same_thread=False  # Allow connection to be used across threads
            )

            # Configure connection
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.row_factory = sqlite3.Row

            return conn

        except sqlite3.Error as e:
            logger.error(f"Failed to create/configure connection: {e}")
            raise

    def _validate_connection(self, conn: sqlite3.Connection) -> bool:
        """
        Validate that a connection is still usable.

        Args:
            conn: The connection to validate

        Returns:
            True if the connection is valid, False otherwise
        """
        try:
            # Simple ping test
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            return True
        except Exception as e:
            logger.debug(f"Connection validation failed: {e}")
            return False

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes all connections."""
        self.close_all()
        return False

    def __del__(self):
        """Destructor - ensures cleanup on garbage collection."""
        if not self._closed:
            logger.warning("ConnectionPool destroyed without calling close_all()")
            try:
                self.close_all()
            except Exception as e:
                logger.error(f"Error during ConnectionPool cleanup: {e}")
