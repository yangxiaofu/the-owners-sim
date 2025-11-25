# Fix Plan: Issue #6 - Single Transaction Rollback Risk

**Priority**: MEDIUM
**Complexity**: Low-Medium
**Estimated Time**: 3-4 hours (1 day)
**Dependencies**: Issue #1 (Incremental Persistence - provides checkpoint infrastructure)

## Problem Statement

### Current Behavior
The entire week simulation executes in a single database transaction:
- Transaction starts before day 1
- All 7 days execute
- Transaction commits after day 7
- **If any day fails, ALL 7 days roll back**

### Impact
- **Data Loss**: Failure on day 7 loses all progress from days 1-6
- **Debugging Difficulty**: Cannot inspect partial results after failure
- **Recovery Complexity**: Must re-simulate entire week after fixing issue
- **Testing Friction**: Cannot examine intermediate states
- **Production Risk**: Single point of failure for multi-day operations

### Example Failure Scenario
```
Day 1: ✅ Game simulated, stats persisted (in transaction)
Day 2: ✅ Free agency signing (in transaction)
Day 3: ✅ Injury update (in transaction)
Day 4: ✅ Coaching change (in transaction)
Day 5: ✅ Trade executed (in transaction)
Day 6: ✅ Calendar advance (in transaction)
Day 7: ❌ Database constraint violation

Result: Days 1-6 LOST - rollback to before week started
```

### Root Cause
`SimulationController` uses template method with single transaction scope:

```python
def simulate_week(self) -> bool:
    """All 7 days in single transaction - all-or-nothing."""
    with self._get_transaction_context() as txn:  # Single transaction
        for _ in range(7):
            if not self.simulate_day():  # Error here rolls back everything
                return False

        txn.commit()  # Only commits if all 7 days succeed

    return True
```

## Solution Architecture

### Overview
Break single transaction into per-day transactions with optional checkpoint savepoints. This provides "progressive persistence" where each day commits independently, reducing rollback scope to single day.

### Design Decision: Per-Day Transactions

**Option A: Per-Day Transactions (Chosen)**
```python
for day in range(7):
    with TransactionContext() as txn:  # New transaction per day
        simulate_day()
        txn.commit()
    # Day commits independently
```

**Pros**:
- ✅ Minimal rollback scope (1 day max)
- ✅ Partial progress always saved
- ✅ Simple to understand
- ✅ Works with existing infrastructure

**Cons**:
- ❌ Cannot roll back entire week if needed
- ❌ Slightly more transaction overhead (~7 BEGINs vs 1)

**Option B: Savepoints After Each Day (Alternative)**
```python
with TransactionContext() as txn:
    for day in range(7):
        savepoint = txn.savepoint(f"day_{day}")
        try:
            simulate_day()
        except:
            txn.rollback_to_savepoint(savepoint)
            raise
    txn.commit()
```

**Pros**:
- ✅ Can still roll back entire week
- ✅ Granular rollback to specific day

**Cons**:
- ❌ More complex error handling
- ❌ Savepoints held for entire week (locks)
- ❌ Still loses all progress on final commit failure

**Decision**: Use **per-day transactions** for simplicity and guaranteed progress. If week-level atomicity is needed in future, add explicit opt-in flag.

### Transaction Modes

Current code uses `IMMEDIATE` mode for all operations. This is correct for per-day transactions:

```python
TransactionMode.IMMEDIATE  # Prevents concurrent writes, good for day simulation
```

Alternative for read-heavy days:
```python
TransactionMode.DEFERRED   # Lazy locking, good if day has no writes
```

**Decision**: Keep `IMMEDIATE` for consistency - performance difference negligible for interactive UI.

## Implementation Plan

### Phase 1: Per-Day Transaction Wrapper (1.5 hours)

**File**: `ui/controllers/simulation_controller.py`

**1.1 Add Transaction Strategy Enum**
```python
from enum import Enum

class SimulationTransactionStrategy(Enum):
    """Control transaction scope during simulation."""
    SINGLE_TRANSACTION = "single"      # Current behavior (all-or-nothing)
    PER_DAY_TRANSACTION = "per_day"    # Each day commits independently
    CHECKPOINT_SAVEPOINTS = "savepoint" # Savepoints with week-level commit
```

**1.2 Add Configuration Property**
```python
class SimulationController(QObject):
    def __init__(self, ...):
        super().__init__()
        # Default to safer per-day transactions
        self._transaction_strategy = SimulationTransactionStrategy.PER_DAY_TRANSACTION

    @property
    def transaction_strategy(self) -> SimulationTransactionStrategy:
        """Get current transaction strategy."""
        return self._transaction_strategy

    @transaction_strategy.setter
    def transaction_strategy(self, strategy: SimulationTransactionStrategy):
        """Set transaction strategy for simulations."""
        self._transaction_strategy = strategy
        logger.info(f"Transaction strategy set to: {strategy.value}")
```

**1.3 Refactor simulate_week() to Use Strategy**
```python
def simulate_week(self) -> Dict[str, Any]:
    """
    Simulate 7 days using configured transaction strategy.

    Returns:
        dict: {
            'success': bool,
            'days_simulated': int,
            'failed_on_day': Optional[int],
            'error': Optional[str]
        }
    """
    if self._transaction_strategy == SimulationTransactionStrategy.SINGLE_TRANSACTION:
        return self._simulate_week_single_transaction()
    elif self._transaction_strategy == SimulationTransactionStrategy.PER_DAY_TRANSACTION:
        return self._simulate_week_per_day_transaction()
    elif self._transaction_strategy == SimulationTransactionStrategy.CHECKPOINT_SAVEPOINTS:
        return self._simulate_week_with_savepoints()
    else:
        raise ValueError(f"Unknown strategy: {self._transaction_strategy}")
```

**1.4 Implement Per-Day Transaction Method**
```python
def _simulate_week_per_day_transaction(self) -> Dict[str, Any]:
    """
    Simulate week with each day in separate transaction.
    Minimizes rollback scope - only current day lost on failure.
    """
    days_completed = 0

    for day_num in range(7):
        try:
            # Each day gets its own transaction
            with self._get_transaction_context() as txn:
                success = self._simulate_single_day()

                if not success:
                    # Day simulation failed - transaction auto-rolls back
                    return {
                        'success': False,
                        'days_simulated': days_completed,
                        'failed_on_day': day_num + 1,
                        'error': 'Day simulation returned failure'
                    }

                # Commit this day's changes
                txn.commit()
                days_completed += 1

                logger.debug(f"Day {day_num + 1}/7 committed successfully")

        except Exception as e:
            # Transaction auto-rolled back by context manager
            logger.error(f"Week simulation failed on day {day_num + 1}: {e}")
            return {
                'success': False,
                'days_simulated': days_completed,
                'failed_on_day': day_num + 1,
                'error': str(e)
            }

    return {
        'success': True,
        'days_simulated': 7,
        'failed_on_day': None,
        'error': None
    }
```

**1.5 Keep Legacy Single-Transaction Method**
```python
def _simulate_week_single_transaction(self) -> Dict[str, Any]:
    """
    Simulate entire week in single transaction (legacy behavior).
    Used for testing or when week-level atomicity is required.
    """
    try:
        with self._get_transaction_context() as txn:
            for day_num in range(7):
                success = self._simulate_single_day()
                if not success:
                    # Rolls back entire week
                    return {
                        'success': False,
                        'days_simulated': 0,
                        'failed_on_day': day_num + 1,
                        'error': 'Day simulation failed'
                    }

            txn.commit()

            return {
                'success': True,
                'days_simulated': 7,
                'failed_on_day': None,
                'error': None
            }

    except Exception as e:
        logger.error(f"Week simulation failed: {e}")
        return {
            'success': False,
            'days_simulated': 0,
            'failed_on_day': None,
            'error': str(e)
        }
```

### Phase 2: Savepoint Strategy (Optional - 1.5 hours)

**2.1 Implement Savepoint-Based Simulation**
```python
def _simulate_week_with_savepoints(self) -> Dict[str, Any]:
    """
    Simulate week with savepoints after each day.
    Allows granular rollback while maintaining week-level atomicity.
    """
    try:
        with self._get_transaction_context() as txn:
            savepoints = []
            days_completed = 0

            for day_num in range(7):
                # Create savepoint before simulating day
                sp_name = f"day_{day_num + 1}_start"
                savepoint = txn.savepoint(sp_name)
                savepoints.append((day_num, savepoint))

                try:
                    success = self._simulate_single_day()

                    if not success:
                        # Rollback to start of this day
                        txn.rollback_to_savepoint(savepoint)
                        raise ValueError(f"Day {day_num + 1} simulation failed")

                    days_completed += 1
                    logger.debug(f"Day {day_num + 1}/7 savepoint created")

                except Exception as day_error:
                    # Rollback to start of this day, then re-raise
                    logger.warning(f"Rolling back day {day_num + 1}: {day_error}")
                    txn.rollback_to_savepoint(savepoint)
                    raise

            # All days succeeded - commit entire week
            txn.commit()

            return {
                'success': True,
                'days_simulated': 7,
                'failed_on_day': None,
                'error': None
            }

    except Exception as e:
        logger.error(f"Week simulation failed: {e}")
        return {
            'success': False,
            'days_simulated': days_completed,
            'failed_on_day': days_completed + 1,
            'error': str(e)
        }
```

### Phase 3: Error Recovery UI (0.5 hours)

**File**: `ui/main_window.py`

**3.1 Show Detailed Error Dialog**
```python
def _sim_week(self):
    """Simulate week with error recovery."""
    result = self._simulation_controller.simulate_week()

    if not result['success']:
        # Show detailed error dialog
        error_msg = (
            f"Week simulation failed on day {result['failed_on_day']}.\n\n"
            f"Days successfully simulated: {result['days_simulated']}\n"
            f"Error: {result['error']}\n\n"
        )

        if result['days_simulated'] > 0:
            error_msg += (
                f"✅ Good news: Days 1-{result['days_simulated']} were saved.\n"
                "You can continue from where you left off."
            )
        else:
            error_msg += (
                "⚠️ No progress was saved.\n"
                "Please check logs and try again."
            )

        QMessageBox.warning(self, "Simulation Error", error_msg)
    else:
        # Success - update UI
        self.statusBar().showMessage(
            f"Week simulated successfully ({result['days_simulated']} days)",
            3000
        )
```

### Phase 4: Testing & Validation (1 hour)

**File**: `tests/ui/test_transaction_strategies.py` (NEW)

**4.1 Unit Tests for Each Strategy**
```python
import pytest
from ui.controllers.simulation_controller import (
    SimulationController,
    SimulationTransactionStrategy
)

def test_per_day_transaction_saves_partial_progress(simulation_controller, mock_backend):
    """Verify per-day strategy saves days 1-3 when day 4 fails."""
    # Setup: Make day 4 fail
    mock_backend.advance_day.side_effect = [
        None,  # Day 1 success
        None,  # Day 2 success
        None,  # Day 3 success
        ValueError("Injected failure"),  # Day 4 fails
    ]

    simulation_controller.transaction_strategy = SimulationTransactionStrategy.PER_DAY_TRANSACTION

    result = simulation_controller.simulate_week()

    # Verify results
    assert result['success'] is False
    assert result['days_simulated'] == 3  # Days 1-3 saved
    assert result['failed_on_day'] == 4

    # Verify database has days 1-3
    state = simulation_controller._data_model.state
    # ... assertions on state ...

def test_single_transaction_loses_all_progress(simulation_controller, mock_backend):
    """Verify single transaction strategy loses all progress on failure."""
    # Setup: Make day 4 fail
    mock_backend.advance_day.side_effect = [
        None, None, None,
        ValueError("Injected failure"),
    ]

    simulation_controller.transaction_strategy = SimulationTransactionStrategy.SINGLE_TRANSACTION

    result = simulation_controller.simulate_week()

    # Verify results
    assert result['success'] is False
    assert result['days_simulated'] == 0  # Nothing saved
    assert result['failed_on_day'] == 4

    # Verify database unchanged
    # ... assertions ...

def test_savepoint_strategy_allows_retry(simulation_controller, mock_backend):
    """Verify savepoint strategy can roll back to specific day."""
    simulation_controller.transaction_strategy = SimulationTransactionStrategy.CHECKPOINT_SAVEPOINTS

    # First attempt: day 5 fails
    mock_backend.advance_day.side_effect = [None, None, None, None, ValueError()]
    result = simulation_controller.simulate_week()

    assert result['days_simulated'] == 4

    # Database should still be at original state (no commit yet)
    # ... assertions ...
```

**4.2 Integration Test with Real Database**
```python
def test_per_day_persistence_real_database(tmp_path, simulation_controller):
    """Integration test with real SQLite database."""
    db_path = tmp_path / "test.db"

    # Initialize database
    # ... setup code ...

    simulation_controller.transaction_strategy = SimulationTransactionStrategy.PER_DAY_TRANSACTION

    # Simulate 3 days successfully
    for _ in range(3):
        simulation_controller.simulate_day()

    # Query database directly
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "SELECT current_date FROM dynasty_state WHERE dynasty_id = ?",
            (dynasty_id,)
        )
        current_date = cursor.fetchone()[0]

    # Verify date advanced 3 days
    # ... assertions ...
```

## Performance Impact

### Transaction Overhead
- **Single Transaction**: 1 BEGIN + 1 COMMIT = ~0.5ms
- **Per-Day Transactions**: 7 BEGINs + 7 COMMITs = ~3.5ms
- **Overhead**: ~3ms per week (~0.1% of 3000ms simulation)

### Disk I/O
- **Single Transaction**: 1 fsync at end
- **Per-Day Transactions**: 7 fsyncs (1 per day)
- **Impact**: ~10-20ms additional I/O (assuming SSD)

**Total Overhead**: ~25ms per week (~0.8% of total time)

### Optimization: Async Commits (Optional)
```python
# In database/connection.py
conn.execute("PRAGMA synchronous = NORMAL")  # Instead of FULL
# Reduces fsync wait time by 50% (less durable but acceptable for game saves)
```

## Risk Assessment

### Low Risks
- Per-day transactions are standard practice
- SQLite handles this pattern efficiently
- Minimal performance impact

### Medium Risks
- **Partial Week State**: Some operations may expect full week atomicity
  - **Mitigation**: Keep single-transaction option for those cases
- **Testing Burden**: Need to test all three strategies
  - **Mitigation**: Focus testing on per-day (default), light testing on others

### Mitigation Strategies
- Default to safest strategy (per-day)
- Document when to use each strategy
- Add validation to detect inconsistent partial states

## Dependencies

### Prerequisites
- `TransactionContext` supports nested transactions (already implemented)
- `CheckpointManager` supports savepoints (already implemented)

### Synergies with Other Fixes
- **Issue #1 (Incremental Persistence)**: Both reduce rollback scope
  - Checkpoint callbacks work naturally with per-day transactions
- **Issue #5 (Progressive UI Updates)**: Per-day commits mean UI always sees latest state
  - No "phantom data" in UI that might roll back

## Implementation Timeline

| Phase | Time | Description |
|-------|------|-------------|
| 1. Per-Day Wrapper | 1.5h | Strategy enum, refactor simulate_week() |
| 2. Savepoint Strategy | 1.5h | Optional savepoint-based approach |
| 3. Error Recovery UI | 0.5h | Show partial progress in error dialog |
| 4. Testing | 1h | Unit + integration tests |
| **Total** | **4.5h** | **~1 day** |

### Testing Time Included
Phase 4 covers all testing needs.

### Grand Total: 4.5 hours (~1 day)

## Acceptance Criteria

1. ✅ Per-day transaction strategy commits after each day
2. ✅ Failure on day 5 preserves days 1-4
3. ✅ Single-transaction strategy still available (opt-in)
4. ✅ Savepoint strategy implemented (optional)
5. ✅ Error dialog shows how many days were saved
6. ✅ Performance overhead <1% of total simulation time
7. ✅ All three strategies tested
8. ✅ Database integrity maintained across all strategies
9. ✅ Existing tests still pass
10. ✅ Documentation updated with strategy recommendations

## Configuration Recommendations

### Default Settings
```python
# For interactive UI simulation (user-driven)
controller.transaction_strategy = SimulationTransactionStrategy.PER_DAY_TRANSACTION

# For background AI simulation (batch processing)
controller.transaction_strategy = SimulationTransactionStrategy.SINGLE_TRANSACTION

# For operations requiring week-level atomicity (e.g., playoffs)
controller.transaction_strategy = SimulationTransactionStrategy.CHECKPOINT_SAVEPOINTS
```

### When to Use Each Strategy

**PER_DAY_TRANSACTION** (Default)
- ✅ Interactive UI simulation
- ✅ Manual "Simulate Week" button
- ✅ Any user-facing operation
- ✅ Development/debugging

**SINGLE_TRANSACTION**
- ✅ Background AI processing
- ✅ Batch simulation (multiple weeks)
- ✅ Unit tests requiring clean rollback
- ✅ Performance-critical operations

**CHECKPOINT_SAVEPOINTS**
- ✅ Playoff weeks (bracket consistency)
- ✅ Draft weeks (pick order integrity)
- ✅ Operations with cross-day dependencies
- ✅ Debugging (can inspect savepoints)

## Future Enhancements

- **Auto-Recovery**: Detect partial week state on app startup, offer to continue
- **Transaction Log**: Record all transactions for audit trail
- **Distributed Transactions**: Support for future cloud sync feature
- **Optimistic Locking**: Allow concurrent simulations in different dynasties

## References

- **SQLite Transactions**: https://www.sqlite.org/lang_transaction.html
- **Savepoints**: https://www.sqlite.org/lang_savepoint.html
- **Existing Code**: `src/database/transaction_context.py` (lines 1-330)
- **Checkpoint Manager**: `src/database/checkpoint_manager.py` (lines 81-403)
- **Similar Pattern**: Draft dialog uses per-pick transactions for same reason