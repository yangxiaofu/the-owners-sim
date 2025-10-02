# Demo Persistence API

A reusable, testable persistence layer for demo applications using composition and the Strategy Pattern.

## Overview

This persistence API provides a flexible, maintainable way to persist game simulation data across different storage backends. It uses **composition over inheritance** with the **Strategy Pattern** for maximum flexibility and testability.

## Design Principles

### Why Composition + Strategy Pattern?

**✅ Advantages:**
- **Loose Coupling**: Components are independent and easily swappable
- **Testable**: Each component can be mocked and tested in isolation
- **Flexible**: Can switch persistence strategies at runtime
- **Single Responsibility**: Each class has one clear purpose
- **Reusable**: Same orchestrator works with different storage strategies

**❌ Avoided Inheritance Because:**
- Creates tight coupling between base and derived classes
- Hard to swap implementations at runtime
- Difficult to test in isolation
- Leads to rigid class hierarchies

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DemoPersister (ABC)                      │
│         Abstract interface for all strategies               │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ├─ DatabaseDemoPersister (SQLite)
                  ├─ FileDemoPersister (JSON/CSV) [Future]
                  └─ InMemoryDemoPersister (Testing) [Future]

┌─────────────────────────────────────────────────────────────┐
│          GamePersistenceOrchestrator                        │
│   Coordinates multiple persistence operations               │
│   - Uses any DemoPersister strategy via composition         │
│   - Manages transactions                                    │
│   - Aggregates results                                      │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Base Interface: `DemoPersister`
Abstract base class defining the contract for all persistence strategies.

```python
from persistence.demo import DemoPersister

class DemoPersister(ABC):
    @abstractmethod
    def persist_game_result(self, game_id, game_data, dynasty_id) -> PersistenceResult

    @abstractmethod
    def persist_player_stats(self, game_id, player_stats, dynasty_id) -> PersistenceResult

    @abstractmethod
    def persist_team_stats(self, game_id, home_stats, away_stats, dynasty_id) -> PersistenceResult

    @abstractmethod
    def update_standings(self, home_team_id, away_team_id, home_score, away_score, dynasty_id, season) -> PersistenceResult

    @abstractmethod
    def begin_transaction(self) -> bool

    @abstractmethod
    def commit_transaction(self) -> bool

    @abstractmethod
    def rollback_transaction(self) -> bool
```

### 2. Result Classes

**`PersistenceResult`**: Single operation result
```python
from persistence.demo import PersistenceResult, PersistenceStatus

result = PersistenceResult(status=PersistenceStatus.SUCCESS)
result.records_persisted = 10
result.processing_time_ms = 5.2
result.add_error("Some error") if error else None
```

**`CompositePersistenceResult`**: Multiple operations aggregated
```python
from persistence.demo import CompositePersistenceResult

composite = CompositePersistenceResult(overall_status=PersistenceStatus.SUCCESS)
composite.add_result("game_result", game_result)
composite.add_result("player_stats", player_stats_result)
```

### 3. Database Strategy: `DatabaseDemoPersister`
SQLite implementation of the persistence strategy.

```python
from persistence.demo import DatabaseDemoPersister

persister = DatabaseDemoPersister("path/to/database.db")
```

**Features:**
- Transaction support with rollback
- Automatic standings calculation
- Player statistics with snap counts
- Performance metrics tracking

### 4. Orchestrator: `GamePersistenceOrchestrator`
Coordinates multiple persistence operations with transaction management.

```python
from persistence.demo import GamePersistenceOrchestrator, DatabaseDemoPersister

# Initialize with strategy injection
persister = DatabaseDemoPersister("demo.db")
orchestrator = GamePersistenceOrchestrator(persister)

# Persist complete game
result = orchestrator.persist_complete_game(
    game_id="game_001",
    game_result=game_result_data,
    player_stats=player_stats_list,
    dynasty_id="my_dynasty",
    season=2024,
    week=1
)
```

## Usage Examples

### Basic Usage (Current Demo)

```python
from persistence.demo import (
    GamePersistenceOrchestrator,
    DatabaseDemoPersister
)

# 1. Initialize persistence strategy
db_persister = DatabaseDemoPersister("demo.db")

# 2. Create orchestrator with strategy
orchestrator = GamePersistenceOrchestrator(db_persister)

# 3. Prepare game data
game_data = {
    'home_team_id': 24,
    'away_team_id': 7,
    'home_score': 21,
    'away_score': 17,
    'total_plays': 150,
    'game_duration_minutes': 180,
    'season': 2024,
    'week': 1
}

# 4. Persist complete game
result = orchestrator.persist_complete_game(
    game_id="browns_vs_vikings",
    game_result=game_data,
    player_stats=player_stats,
    dynasty_id="demo_dynasty",
    season=2024,
    week=1
)

# 5. Check results
if result.success:
    print(f"✅ Persisted {result.total_records_persisted} records")
    print(f"⏱️ Processing time: {result.total_processing_time_ms:.2f}ms")
else:
    print(f"❌ Errors: {result.all_errors}")
```

### Advanced Usage: Batch Persistence

```python
# Persist multiple games
games = [
    {
        'game_id': 'game_001',
        'game_result': game1_data,
        'player_stats': game1_player_stats,
        'season': 2024,
        'week': 1
    },
    {
        'game_id': 'game_002',
        'game_result': game2_data,
        'player_stats': game2_player_stats,
        'season': 2024,
        'week': 1
    }
]

results = orchestrator.persist_game_batch(games, dynasty_id="my_dynasty")

for result in results:
    print(f"Game: {result.success} - {result.total_records_persisted} records")
```

### Reusability: Different Strategies

The beauty of this design is that you can easily swap persistence strategies:

```python
# Demo 1: SQLite database
db_orchestrator = GamePersistenceOrchestrator(
    DatabaseDemoPersister("demo1.db")
)

# Demo 2: File-based (future implementation)
file_orchestrator = GamePersistenceOrchestrator(
    FileDemoPersister("demo2.json")
)

# Demo 3: In-memory for testing (future implementation)
test_orchestrator = GamePersistenceOrchestrator(
    InMemoryDemoPersister()
)

# All use the same orchestrator interface!
result1 = db_orchestrator.persist_complete_game(...)
result2 = file_orchestrator.persist_complete_game(...)
result3 = test_orchestrator.persist_complete_game(...)
```

### Testing with Mocks

```python
from unittest.mock import Mock
from persistence.demo import GamePersistenceOrchestrator, PersistenceResult, PersistenceStatus

# Create a mock persister
mock_persister = Mock()
mock_persister.persist_game_result.return_value = PersistenceResult(
    status=PersistenceStatus.SUCCESS,
    records_persisted=1
)

# Test orchestrator with mock
orchestrator = GamePersistenceOrchestrator(mock_persister)
result = orchestrator.persist_complete_game(...)

# Verify mock was called correctly
mock_persister.persist_game_result.assert_called_once()
```

## Database Schema

The demo database requires these tables:

```sql
-- Games table
CREATE TABLE games (
    game_id TEXT PRIMARY KEY,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,
    game_type TEXT DEFAULT 'regular',
    home_team_id INTEGER NOT NULL,
    away_team_id INTEGER NOT NULL,
    home_score INTEGER NOT NULL,
    away_score INTEGER NOT NULL,
    total_plays INTEGER,
    game_duration_minutes INTEGER,
    overtime_periods INTEGER DEFAULT 0,
    created_at TEXT
);

-- Player statistics table
CREATE TABLE player_game_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    game_id TEXT NOT NULL,
    player_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    team_id INTEGER NOT NULL,
    position TEXT NOT NULL,
    passing_yards INTEGER DEFAULT 0,
    passing_tds INTEGER DEFAULT 0,
    -- ... more stats fields
);

-- Standings table
CREATE TABLE standings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    team_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    ties INTEGER DEFAULT 0,
    points_for INTEGER DEFAULT 0,
    points_against INTEGER DEFAULT 0,
    -- ... more standings fields
);
```

Use `demo/game_simulation_persistance_demo/initialize_demo_db.py` to create tables.

## Error Handling

The API provides comprehensive error handling:

```python
result = orchestrator.persist_complete_game(...)

if result.success:
    # Success case
    print(f"Persisted: {result.total_records_persisted}")
elif result.overall_status == PersistenceStatus.PARTIAL_SUCCESS:
    # Some operations succeeded
    print(f"Partial success with warnings: {result.all_warnings}")
elif result.overall_status == PersistenceStatus.ROLLBACK:
    # Transaction was rolled back
    print(f"Rollback performed: {result.all_errors}")
else:
    # Complete failure
    print(f"Failed: {result.all_errors}")
```

## Performance Metrics

Each operation tracks detailed metrics:

```python
result = orchestrator.persist_complete_game(...)

print(f"Records persisted: {result.total_records_persisted}")
print(f"Records failed: {result.total_records_failed}")
print(f"Processing time: {result.total_processing_time_ms:.2f}ms")
print(f"Success rate: {result.success_rate:.1f}%")

# Get operation breakdown
for operation_name, operation_result in result.results.items():
    print(f"{operation_name}: {operation_result.records_persisted} records "
          f"in {operation_result.processing_time_ms:.2f}ms")

# Get orchestrator statistics
stats = orchestrator.get_orchestrator_statistics()
print(f"Total operations: {stats['orchestrator']['total_operations']}")
print(f"Success rate: {stats['orchestrator']['success_rate']:.1f}%")
```

## Future Extensions

The architecture supports easy extension:

1. **File-Based Persistence**
   ```python
   class FileDemoPersister(DemoPersister):
       def persist_game_result(self, ...):
           # Write to JSON/CSV file
   ```

2. **In-Memory Persistence** (for testing)
   ```python
   class InMemoryDemoPersister(DemoPersister):
       def __init__(self):
           self.games = {}
           self.player_stats = []
   ```

3. **Cloud Storage Persistence**
   ```python
   class CloudDemoPersister(DemoPersister):
       def persist_game_result(self, ...):
           # Upload to S3/GCS
   ```

All would work with the same `GamePersistenceOrchestrator`!

## Best Practices

1. **Always use transactions** for atomic operations
2. **Check result.success** before assuming persistence succeeded
3. **Log warnings** even on success for debugging
4. **Use dynasty_id** for multi-dynasty isolation
5. **Initialize database schema** before first use
6. **Test with mocks** to avoid database dependencies

## License

Part of The Owners Sim project.
