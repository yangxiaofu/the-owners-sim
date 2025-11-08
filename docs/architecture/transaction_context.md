# TransactionContext Architecture

## Overview

The `TransactionContext` class provides a robust, pythonic context manager for atomic multi-operation database transactions in the NFL simulation system. It ensures ACID properties (Atomicity, Consistency, Isolation, Durability) with automatic commit/rollback handling and support for nested transactions.

## Features

### Core Functionality

1. **Automatic Transaction Management**
   - Auto-BEGIN on context entry
   - Auto-COMMIT on successful completion
   - Auto-ROLLBACK on exception

2. **Nested Transaction Support**
   - Uses SQLite savepoints for nested transactions
   - Inner transaction rollback doesn't affect outer transaction
   - Multiple nesting levels supported

3. **Multiple Transaction Modes**
   - `DEFERRED` (default): Lock acquired on first write operation
   - `IMMEDIATE`: Lock acquired immediately (prevents write conflicts)
   - `EXCLUSIVE`: Exclusive lock acquired immediately (blocks all connections)

4. **Transaction State Tracking**
   - `INACTIVE`: Transaction not started
   - `ACTIVE`: Transaction in progress
   - `COMMITTED`: Transaction successfully committed
   - `ROLLED_BACK`: Transaction rolled back

5. **Explicit Control**
   - Manual `commit()` within transaction
   - Manual `rollback()` within transaction
   - Continued operations after explicit commit

## Usage Patterns

### Basic Transaction

```python
from database.transaction_context import TransactionContext

conn = get_database_connection()
cursor = conn.cursor()

with TransactionContext(conn) as tx:
    cursor.execute("INSERT INTO players ...")
    cursor.execute("UPDATE contracts ...")
    # Auto-commits on success, auto-rolls back on exception
```

### Transaction Modes

```python
# DEFERRED (default) - lock on first write
with TransactionContext(conn, mode="DEFERRED") as tx:
    cursor.execute("SELECT * FROM players")  # No lock
    cursor.execute("INSERT INTO players ...")  # Lock acquired here

# IMMEDIATE - immediate write lock (recommended for write operations)
with TransactionContext(conn, mode="IMMEDIATE") as tx:
    cursor.execute("INSERT INTO players ...")  # Lock already held
    cursor.execute("UPDATE contracts ...")

# EXCLUSIVE - exclusive lock (critical sections)
with TransactionContext(conn, mode="EXCLUSIVE") as tx:
    cursor.execute("DELETE FROM draft_picks WHERE ...")
```

### Nested Transactions (Savepoints)

```python
with TransactionContext(conn) as outer_tx:
    cursor.execute("INSERT INTO players ...")

    # Nested transaction uses savepoint
    with TransactionContext(conn) as inner_tx:
        cursor.execute("UPDATE contracts ...")
        # If this fails, only inner transaction rolls back

    # Continue outer transaction
    cursor.execute("INSERT INTO trade_history ...")
```

### Explicit Commit/Rollback

```python
with TransactionContext(conn) as tx:
    cursor.execute("INSERT INTO players ...")

    # Conditional logic
    if validate_player(player_data):
        tx.commit()  # Explicit commit
        cursor.execute("INSERT INTO history ...")
    else:
        tx.rollback()  # Explicit rollback
        # Transaction ends here
```

### Convenience Function

```python
from database.transaction_context import transaction

# Shorter syntax
with transaction(conn, mode="IMMEDIATE") as tx:
    cursor.execute("INSERT ...")
    cursor.execute("UPDATE ...")
```

## Real-World Examples

### Player Trade Transaction

```python
def execute_player_trade(conn, player_id, from_team, to_team):
    """Execute a complete player trade with cap validation."""
    cursor = conn.cursor()

    with TransactionContext(conn, mode="IMMEDIATE") as tx:
        # Step 1: Get player salary
        cursor.execute("SELECT salary FROM players WHERE id = ?", (player_id,))
        salary = cursor.fetchone()[0]

        # Step 2: Verify cap space
        cursor.execute("SELECT cap_space, cap_used FROM team_cap WHERE team_id = ?", (to_team,))
        cap_space, cap_used = cursor.fetchone()

        if cap_space - cap_used < salary:
            raise ValueError(f"Insufficient cap space: need ${salary}, have ${cap_space - cap_used}")

        # Step 3: Update player's team
        cursor.execute("UPDATE players SET team_id = ? WHERE id = ?", (to_team, player_id))

        # Step 4: Update cap space for both teams
        cursor.execute("UPDATE team_cap SET cap_used = cap_used - ? WHERE team_id = ?",
                      (salary, from_team))
        cursor.execute("UPDATE team_cap SET cap_used = cap_used + ? WHERE team_id = ?",
                      (salary, to_team))

        # Step 5: Record trade history
        cursor.execute("""
            INSERT INTO trade_history (player_id, from_team, to_team, trade_date)
            VALUES (?, ?, ?, date('now'))
        """, (player_id, from_team, to_team))

        # All changes committed atomically
```

### Draft Selection with Validation

```python
def record_draft_pick(conn, pick_number, team_id, player_id):
    """Record a draft pick with validation."""
    cursor = conn.cursor()

    with TransactionContext(conn, mode="IMMEDIATE") as tx:
        # Insert draft pick
        cursor.execute("""
            INSERT INTO draft_picks (pick_number, team_id, player_id)
            VALUES (?, ?, ?)
        """, (pick_number, team_id, player_id))

        # Validate pick
        cursor.execute("""
            SELECT p.position, t.roster_needs
            FROM players p
            JOIN teams t ON t.team_id = ?
            WHERE p.id = ?
        """, (team_id, player_id))

        position, roster_needs = cursor.fetchone()

        if position not in roster_needs:
            # Invalid pick, rollback
            tx.rollback()
            raise ValueError(f"Team {team_id} doesn't need position {position}")

        # Valid pick, update roster
        cursor.execute("""
            INSERT INTO team_rosters (team_id, player_id)
            VALUES (?, ?)
        """, (team_id, player_id))
```

### Multi-Table Game Result Recording

```python
def record_game_result(conn, game_data):
    """Record complete game result across multiple tables."""
    cursor = conn.cursor()

    with TransactionContext(conn, mode="IMMEDIATE") as tx:
        # Insert game record
        cursor.execute("""
            INSERT INTO games (game_id, home_team, away_team, home_score, away_score, ...)
            VALUES (?, ?, ?, ?, ?, ...)
        """, game_data)

        # Update team standings
        cursor.execute("""
            UPDATE standings
            SET wins = wins + 1, points_for = points_for + ?
            WHERE team_id = ?
        """, (game_data['winner_score'], game_data['winner_id']))

        cursor.execute("""
            UPDATE standings
            SET losses = losses + 1, points_against = points_against + ?
            WHERE team_id = ?
        """, (game_data['loser_score'], game_data['loser_id']))

        # Insert player statistics
        for player_stats in game_data['player_stats']:
            cursor.execute("""
                INSERT INTO player_game_stats (game_id, player_id, ...)
                VALUES (?, ?, ...)
            """, player_stats)

        # All changes committed atomically
```

## Architecture Decisions

### Why Context Manager?

1. **Pythonic**: Follows Python best practices for resource management
2. **Safe**: Guarantees cleanup even if exceptions occur
3. **Readable**: Clear scope of transaction boundaries
4. **Composable**: Easy to nest transactions

### Why Savepoints for Nested Transactions?

1. **Isolation**: Inner transaction failures don't affect outer transaction
2. **Flexibility**: Can rollback partial work while continuing outer transaction
3. **SQLite Support**: Native SQLite feature for nested transactions

### Transaction Mode Selection

- **DEFERRED** (default): Best for read-mostly transactions
- **IMMEDIATE**: Best for write-heavy transactions (recommended for most operations)
- **EXCLUSIVE**: Best for critical sections requiring exclusive access

## Error Handling

### Automatic Rollback

```python
try:
    with TransactionContext(conn) as tx:
        cursor.execute("INSERT ...")
        raise Exception("Something went wrong")
        # Automatic rollback on exception
except Exception as e:
    print(f"Transaction failed: {e}")
    # Data already rolled back
```

### Manual Error Handling

```python
with TransactionContext(conn) as tx:
    try:
        cursor.execute("INSERT ...")
        cursor.execute("UPDATE ...")
    except sqlite3.IntegrityError as e:
        # Handle specific error
        tx.rollback()
        raise
```

### Nested Transaction Errors

```python
with TransactionContext(conn) as outer_tx:
    cursor.execute("INSERT INTO players ...")

    try:
        with TransactionContext(conn) as inner_tx:
            cursor.execute("INSERT INTO contracts ...")
            raise ValueError("Contract invalid")
            # Inner transaction rolls back
    except ValueError:
        pass  # Handled gracefully

    # Outer transaction continues normally
    cursor.execute("INSERT INTO history ...")
```

## Testing

### Unit Tests

Comprehensive test suite available in `tests/database/test_transaction_context.py`:

- Basic transaction functionality (25 tests)
- Transaction modes
- Nested transactions
- Error handling
- State tracking
- Real-world scenarios

Run tests:
```bash
python -m pytest tests/database/test_transaction_context.py -v
```

### Demo Script

Interactive demo available in `demo/transaction_context_demo.py`:

```bash
PYTHONPATH=src python demo/transaction_context_demo.py
```

Demonstrates:
- Basic transaction usage
- Transaction modes
- Nested transactions
- Real-world NFL simulation scenarios
- Explicit commit/rollback
- Convenience function

## Performance Considerations

### Transaction Mode Impact

1. **DEFERRED**: Fastest for read-heavy operations (no lock until write)
2. **IMMEDIATE**: Best for write operations (prevents lock escalation conflicts)
3. **EXCLUSIVE**: Slowest (blocks all other connections)

### Best Practices

1. **Keep transactions short**: Minimize time holding locks
2. **Use IMMEDIATE for writes**: Prevents lock conflicts
3. **Batch operations**: Group related operations in single transaction
4. **Avoid nested transactions unless necessary**: Each savepoint has overhead

## Integration with Existing Code

### Refactoring Manual Transactions

Before:
```python
conn = get_connection()
cursor = conn.cursor()
try:
    cursor.execute("INSERT ...")
    cursor.execute("UPDATE ...")
    conn.commit()
except Exception as e:
    conn.rollback()
    raise
```

After:
```python
conn = get_connection()
cursor = conn.cursor()
with TransactionContext(conn) as tx:
    cursor.execute("INSERT ...")
    cursor.execute("UPDATE ...")
```

### Using with DatabaseConnection

```python
from database import DatabaseConnection, TransactionContext

db_conn = DatabaseConnection("data/database/nfl_simulation.db")
conn = db_conn.get_connection()
cursor = conn.cursor()

with TransactionContext(conn, mode="IMMEDIATE") as tx:
    # Perform database operations
    cursor.execute("INSERT ...")
    cursor.execute("UPDATE ...")
```

## Future Enhancements

Potential future improvements:

1. **Transaction Statistics**: Track commit/rollback rates
2. **Deadlock Detection**: Automatic retry with exponential backoff
3. **Transaction Timeouts**: Configurable timeout for long-running transactions
4. **Transaction Logging**: Detailed audit trail of all transactions
5. **Connection Pooling**: Integration with connection pool for multi-threaded usage

## References

- SQLite Transaction Documentation: https://www.sqlite.org/lang_transaction.html
- SQLite Savepoint Documentation: https://www.sqlite.org/lang_savepoint.html
- Python Context Managers: https://docs.python.org/3/reference/datamodel.html#context-managers
- ACID Properties: https://en.wikipedia.org/wiki/ACID

## Module API

### TransactionContext

```python
class TransactionContext:
    def __init__(
        self,
        connection: sqlite3.Connection,
        mode: Literal["DEFERRED", "IMMEDIATE", "EXCLUSIVE"] = "DEFERRED"
    )

    def __enter__(self) -> "TransactionContext"
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool

    def commit(self) -> None
    def rollback(self) -> None

    @property
    def is_active(self) -> bool

    @property
    def is_committed(self) -> bool

    @property
    def is_rolled_back(self) -> bool
```

### TransactionState

```python
class TransactionState(Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
```

### transaction()

```python
def transaction(
    connection: sqlite3.Connection,
    mode: Literal["DEFERRED", "IMMEDIATE", "EXCLUSIVE"] = "DEFERRED"
) -> TransactionContext
```

## See Also

- `docs/schema/database_schema.md` - Database schema documentation
- `docs/architecture/ui_layer_separation.md` - UI architecture (uses transactions)
- `docs/plans/salary_cap_plan.md` - Salary cap system (uses transactions)
