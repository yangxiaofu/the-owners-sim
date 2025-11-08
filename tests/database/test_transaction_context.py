"""
Tests for TransactionContext

Validates atomic multi-operation database transactions with:
- Auto-commit on success
- Auto-rollback on exception
- Nested transaction support (savepoints)
- Multiple transaction modes
- Transaction state tracking
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path

from database.transaction_context import (
    TransactionContext,
    TransactionState,
    transaction
)


@pytest.fixture
def test_db():
    """Create a temporary test database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    conn = sqlite3.connect(db_path)

    # Create test table
    conn.execute('''
        CREATE TABLE test_players (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            team TEXT,
            score INTEGER DEFAULT 0
        )
    ''')
    conn.commit()

    yield conn

    conn.close()
    Path(db_path).unlink()


class TestBasicTransactionContext:
    """Test basic transaction context functionality."""

    def test_auto_commit_on_success(self, test_db):
        """Test that transaction auto-commits on successful completion."""
        cursor = test_db.cursor()

        with TransactionContext(test_db) as tx:
            cursor.execute("INSERT INTO test_players (name, team) VALUES (?, ?)", ("Player 1", "Team A"))
            cursor.execute("INSERT INTO test_players (name, team) VALUES (?, ?)", ("Player 2", "Team B"))
            assert tx.is_active

        # Verify data was committed
        cursor.execute("SELECT COUNT(*) FROM test_players")
        count = cursor.fetchone()[0]
        assert count == 2

    def test_auto_rollback_on_exception(self, test_db):
        """Test that transaction auto-rolls back on exception."""
        cursor = test_db.cursor()

        try:
            with TransactionContext(test_db) as tx:
                cursor.execute("INSERT INTO test_players (name, team) VALUES (?, ?)", ("Player 1", "Team A"))
                assert tx.is_active
                # Force an error
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Verify data was rolled back
        cursor.execute("SELECT COUNT(*) FROM test_players")
        count = cursor.fetchone()[0]
        assert count == 0

    def test_explicit_commit(self, test_db):
        """Test explicit commit within transaction."""
        cursor = test_db.cursor()

        with TransactionContext(test_db) as tx:
            cursor.execute("INSERT INTO test_players (name, team) VALUES (?, ?)", ("Player 1", "Team A"))
            tx.commit()
            assert tx.is_committed

            # Further operations after explicit commit
            cursor.execute("INSERT INTO test_players (name, team) VALUES (?, ?)", ("Player 2", "Team B"))

        # Both inserts should be committed
        cursor.execute("SELECT COUNT(*) FROM test_players")
        count = cursor.fetchone()[0]
        assert count == 2

    def test_explicit_rollback(self, test_db):
        """Test explicit rollback within transaction."""
        cursor = test_db.cursor()

        with TransactionContext(test_db) as tx:
            cursor.execute("INSERT INTO test_players (name, team) VALUES (?, ?)", ("Player 1", "Team A"))
            tx.rollback()
            assert tx.is_rolled_back

        # Verify data was rolled back
        cursor.execute("SELECT COUNT(*) FROM test_players")
        count = cursor.fetchone()[0]
        assert count == 0

    def test_transaction_state_tracking(self, test_db):
        """Test transaction state changes throughout lifecycle."""
        tx = TransactionContext(test_db)

        # Initial state
        assert tx.state == TransactionState.INACTIVE
        assert not tx.is_active

        # Active state
        tx.__enter__()
        assert tx.state == TransactionState.ACTIVE
        assert tx.is_active
        assert not tx.is_committed
        assert not tx.is_rolled_back

        # Committed state
        tx.commit()
        assert tx.state == TransactionState.COMMITTED
        assert tx.is_committed
        assert not tx.is_active

        # Cleanup
        tx.__exit__(None, None, None)


class TestTransactionModes:
    """Test different transaction isolation modes."""

    def test_deferred_mode(self, test_db):
        """Test DEFERRED transaction mode (default)."""
        cursor = test_db.cursor()

        with TransactionContext(test_db, mode="DEFERRED") as tx:
            assert tx.mode == "DEFERRED"
            cursor.execute("INSERT INTO test_players (name, team) VALUES (?, ?)", ("Player 1", "Team A"))

        cursor.execute("SELECT COUNT(*) FROM test_players")
        assert cursor.fetchone()[0] == 1

    def test_immediate_mode(self, test_db):
        """Test IMMEDIATE transaction mode (immediate write lock)."""
        cursor = test_db.cursor()

        with TransactionContext(test_db, mode="IMMEDIATE") as tx:
            assert tx.mode == "IMMEDIATE"
            cursor.execute("INSERT INTO test_players (name, team) VALUES (?, ?)", ("Player 1", "Team A"))

        cursor.execute("SELECT COUNT(*) FROM test_players")
        assert cursor.fetchone()[0] == 1

    def test_exclusive_mode(self, test_db):
        """Test EXCLUSIVE transaction mode (exclusive lock)."""
        cursor = test_db.cursor()

        with TransactionContext(test_db, mode="EXCLUSIVE") as tx:
            assert tx.mode == "EXCLUSIVE"
            cursor.execute("INSERT INTO test_players (name, team) VALUES (?, ?)", ("Player 1", "Team A"))

        cursor.execute("SELECT COUNT(*) FROM test_players")
        assert cursor.fetchone()[0] == 1

    def test_invalid_mode_raises_error(self, test_db):
        """Test that invalid transaction mode raises ValueError."""
        with pytest.raises(ValueError, match="Invalid transaction mode"):
            TransactionContext(test_db, mode="INVALID")


class TestNestedTransactions:
    """Test nested transaction support using savepoints."""

    def test_nested_transaction_commit(self, test_db):
        """Test nested transaction commits correctly."""
        cursor = test_db.cursor()

        with TransactionContext(test_db) as outer_tx:
            cursor.execute("INSERT INTO test_players (name, team) VALUES (?, ?)", ("Player 1", "Team A"))

            with TransactionContext(test_db) as inner_tx:
                assert inner_tx.is_nested
                assert inner_tx.savepoint_name is not None
                cursor.execute("INSERT INTO test_players (name, team) VALUES (?, ?)", ("Player 2", "Team B"))

            # Inner transaction committed, continue outer
            cursor.execute("INSERT INTO test_players (name, team) VALUES (?, ?)", ("Player 3", "Team C"))

        # All inserts should be committed
        cursor.execute("SELECT COUNT(*) FROM test_players")
        assert cursor.fetchone()[0] == 3

    def test_nested_transaction_rollback(self, test_db):
        """Test nested transaction rollback doesn't affect outer transaction."""
        cursor = test_db.cursor()

        with TransactionContext(test_db) as outer_tx:
            cursor.execute("INSERT INTO test_players (name, team) VALUES (?, ?)", ("Player 1", "Team A"))

            try:
                with TransactionContext(test_db) as inner_tx:
                    assert inner_tx.is_nested
                    cursor.execute("INSERT INTO test_players (name, team) VALUES (?, ?)", ("Player 2", "Team B"))
                    raise ValueError("Rollback inner transaction")
            except ValueError:
                pass

            # Continue outer transaction after inner rollback
            cursor.execute("INSERT INTO test_players (name, team) VALUES (?, ?)", ("Player 3", "Team C"))

        # Only outer transaction inserts should be committed
        cursor.execute("SELECT COUNT(*) FROM test_players")
        count = cursor.fetchone()[0]
        assert count == 2  # Player 1 and Player 3, but not Player 2

    def test_multiple_nested_levels(self, test_db):
        """Test multiple levels of nested transactions."""
        cursor = test_db.cursor()

        with TransactionContext(test_db) as level1:
            cursor.execute("INSERT INTO test_players (name, team) VALUES (?, ?)", ("L1", "Team A"))

            with TransactionContext(test_db) as level2:
                cursor.execute("INSERT INTO test_players (name, team) VALUES (?, ?)", ("L2", "Team B"))

                with TransactionContext(test_db) as level3:
                    cursor.execute("INSERT INTO test_players (name, team) VALUES (?, ?)", ("L3", "Team C"))

        cursor.execute("SELECT COUNT(*) FROM test_players")
        assert cursor.fetchone()[0] == 3


class TestErrorHandling:
    """Test error handling and validation."""

    def test_none_connection_raises_error(self):
        """Test that None connection raises ValueError."""
        with pytest.raises(ValueError, match="Connection cannot be None"):
            TransactionContext(None)

    def test_invalid_connection_type_raises_error(self):
        """Test that invalid connection type raises TypeError."""
        with pytest.raises(TypeError, match="Expected sqlite3.Connection"):
            TransactionContext("not a connection")

    def test_commit_when_not_active_raises_error(self, test_db):
        """Test that commit when not active raises RuntimeError."""
        tx = TransactionContext(test_db)

        with pytest.raises(RuntimeError, match="Cannot commit transaction in state: inactive"):
            tx.commit()

    def test_rollback_when_not_active_raises_error(self, test_db):
        """Test that rollback when not active raises RuntimeError."""
        tx = TransactionContext(test_db)

        with pytest.raises(RuntimeError, match="Cannot rollback transaction in state: inactive"):
            tx.rollback()

    def test_database_error_handling(self, test_db):
        """Test handling of database errors during transaction."""
        cursor = test_db.cursor()

        try:
            with TransactionContext(test_db) as tx:
                cursor.execute("INSERT INTO test_players (name, team) VALUES (?, ?)", ("Player 1", "Team A"))
                # Try to insert into non-existent table
                cursor.execute("INSERT INTO nonexistent_table VALUES (1, 2)")
        except sqlite3.OperationalError:
            pass

        # Verify rollback occurred
        cursor.execute("SELECT COUNT(*) FROM test_players")
        assert cursor.fetchone()[0] == 0


class TestConvenienceFunction:
    """Test transaction() convenience function."""

    def test_transaction_convenience_function(self, test_db):
        """Test that transaction() convenience function works correctly."""
        cursor = test_db.cursor()

        with transaction(test_db) as tx:
            assert isinstance(tx, TransactionContext)
            cursor.execute("INSERT INTO test_players (name, team) VALUES (?, ?)", ("Player 1", "Team A"))

        cursor.execute("SELECT COUNT(*) FROM test_players")
        assert cursor.fetchone()[0] == 1

    def test_transaction_function_with_mode(self, test_db):
        """Test transaction() function with custom mode."""
        cursor = test_db.cursor()

        with transaction(test_db, mode="IMMEDIATE") as tx:
            assert tx.mode == "IMMEDIATE"
            cursor.execute("INSERT INTO test_players (name, team) VALUES (?, ?)", ("Player 1", "Team A"))

        cursor.execute("SELECT COUNT(*) FROM test_players")
        assert cursor.fetchone()[0] == 1


class TestComplexTransactionScenarios:
    """Test complex real-world transaction scenarios."""

    def test_multi_table_transaction(self, test_db):
        """Test transaction spanning multiple tables."""
        cursor = test_db.cursor()

        # Create second table
        cursor.execute('''
            CREATE TABLE test_contracts (
                id INTEGER PRIMARY KEY,
                player_id INTEGER,
                salary INTEGER,
                FOREIGN KEY (player_id) REFERENCES test_players(id)
            )
        ''')

        with TransactionContext(test_db) as tx:
            # Insert player
            cursor.execute("INSERT INTO test_players (name, team) VALUES (?, ?)", ("Player 1", "Team A"))
            player_id = cursor.lastrowid

            # Insert contract
            cursor.execute("INSERT INTO test_contracts (player_id, salary) VALUES (?, ?)", (player_id, 5000000))

        # Verify both inserts committed
        cursor.execute("SELECT COUNT(*) FROM test_players")
        assert cursor.fetchone()[0] == 1

        cursor.execute("SELECT COUNT(*) FROM test_contracts")
        assert cursor.fetchone()[0] == 1

    def test_conditional_rollback_scenario(self, test_db):
        """Test conditional rollback based on business logic."""
        cursor = test_db.cursor()

        with TransactionContext(test_db) as tx:
            cursor.execute("INSERT INTO test_players (name, team, score) VALUES (?, ?, ?)",
                          ("Player 1", "Team A", 100))

            cursor.execute("SELECT score FROM test_players WHERE name = ?", ("Player 1",))
            score = cursor.fetchone()[0]

            if score < 200:
                # Business rule: score must be at least 200
                tx.rollback()

        # Verify rollback occurred
        cursor.execute("SELECT COUNT(*) FROM test_players")
        assert cursor.fetchone()[0] == 0

    def test_partial_commit_scenario(self, test_db):
        """Test scenario with partial commit and continued transaction."""
        cursor = test_db.cursor()

        with TransactionContext(test_db) as tx:
            # First batch
            cursor.execute("INSERT INTO test_players (name, team) VALUES (?, ?)", ("Player 1", "Team A"))
            cursor.execute("INSERT INTO test_players (name, team) VALUES (?, ?)", ("Player 2", "Team A"))
            tx.commit()

            # Second batch (new operations after commit)
            cursor.execute("INSERT INTO test_players (name, team) VALUES (?, ?)", ("Player 3", "Team B"))

        # All inserts should be committed
        cursor.execute("SELECT COUNT(*) FROM test_players")
        assert cursor.fetchone()[0] == 3


class TestTransactionRepr:
    """Test string representation of transaction context."""

    def test_transaction_repr_basic(self, test_db):
        """Test __repr__ for basic transaction."""
        tx = TransactionContext(test_db)
        repr_str = repr(tx)

        assert "TransactionContext" in repr_str
        assert "mode=DEFERRED" in repr_str
        assert "state=inactive" in repr_str

    def test_transaction_repr_with_mode(self, test_db):
        """Test __repr__ includes transaction mode."""
        tx = TransactionContext(test_db, mode="IMMEDIATE")
        repr_str = repr(tx)

        assert "mode=IMMEDIATE" in repr_str

    def test_transaction_repr_nested(self, test_db):
        """Test __repr__ for nested transaction shows savepoint."""
        with TransactionContext(test_db):
            tx = TransactionContext(test_db)
            tx.__enter__()
            repr_str = repr(tx)

            assert "savepoint=" in repr_str
            tx.__exit__(None, None, None)
