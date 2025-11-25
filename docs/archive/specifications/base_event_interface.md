# BaseEvent Interface Specification

**Version:** 1.1.0
**Last Updated:** 2025-10-02
**Status:** Implemented

---

## 1. Overview

### Purpose
The BaseEvent interface provides a unified abstraction for all simulation events in The Owners Sim. It enables polymorphic storage and retrieval of different event types (games, scouting, media, trades, etc.) through a single database API while supporting both parameterized (replay-able) and result-based (historical) event patterns.

### Key Concepts

**Event Types:**
- **Parameterized Events**: Events defined by input parameters that can be scheduled and simulated later (e.g., GameEvent)
- **Result-Based Events**: Events where the value is in the output, not the input (e.g., ScoutingEvent)

**Three-Part Data Structure:**
```python
{
    "parameters": {...},  # Input values for recreation/replay
    "results": {...},     # Output after execution (optional, cached)
    "metadata": {...}     # Additional context
}
```

### Design Patterns
- **Template Method Pattern**: Common event lifecycle (validate → simulate → persist)
- **Strategy Pattern**: Each event type implements its own simulation behavior
- **Abstract Base Class**: Python ABC for interface enforcement

---

## 2. Interface Definition

### Base Class

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional
import uuid

class BaseEvent(ABC):
    """Abstract base class for all simulation events"""

    def __init__(self, event_id: Optional[str] = None,
                 timestamp: Optional[datetime] = None):
        self.event_id = event_id or str(uuid.uuid4())
        self.timestamp = timestamp or datetime.now()
```

---

## 3. Required Methods (Abstract)

### 3.1 get_event_type()

**Signature:**
```python
@abstractmethod
def get_event_type(self) -> str:
    """Return the event type identifier"""
    pass
```

**Purpose:** Returns a string identifier used for:
- Database storage and querying
- Event reconstruction from database
- Filtering events by type

**Examples:**
- `"GAME"` - NFL game simulation
- `"SCOUTING"` - Player scouting reports
- `"MEDIA"` - AI-generated media content
- `"TRADE"` - Player/pick trades
- `"INJURY"` - Player injury events
- `"DRAFT"` - Draft selections

**Returns:** String identifier (uppercase convention recommended)

---

### 3.2 simulate()

**Signature:**
```python
@abstractmethod
def simulate(self) -> EventResult:
    """Execute the event and return standardized result"""
    pass
```

**Purpose:** Core event execution method. Each event type implements its own simulation logic:
- **GameEvent**: Runs FullGameSimulator to simulate complete NFL game
- **ScoutingEvent**: Generates player evaluation reports
- **MediaEvent**: Generates AI content (press conferences, articles)

**Returns:** `EventResult` object with:
```python
@dataclass
class EventResult:
    event_id: str
    event_type: str
    success: bool
    timestamp: datetime
    data: Dict[str, Any]
    error_message: Optional[str] = None
```

**Error Handling:** Should return `EventResult` with `success=False` and `error_message` rather than raising exceptions.

---

### 3.3 _get_parameters()

**Signature:**
```python
@abstractmethod
def _get_parameters(self) -> Dict[str, Any]:
    """Return parameters needed to recreate/replay this event"""
    pass
```

**Purpose:** Returns input values that define how to execute the event.

**Use Cases:**
- Scheduling events before execution
- Recreating events from database
- Event replay/simulation

**Examples:**

**GameEvent (Parameterized):**
```python
def _get_parameters(self) -> Dict[str, Any]:
    return {
        "away_team_id": 22,
        "home_team_id": 23,
        "week": 15,
        "season": 2024,
        "game_date": "2024-12-15T13:00:00",
        "overtime_type": "regular_season"
    }
```

**ScoutingEvent (Minimal):**
```python
def _get_parameters(self) -> Dict[str, Any]:
    return {
        "scout_type": "college",
        "target_positions": ["QB", "WR"],
        "num_players": 5
    }
```

**Returns:** Dictionary of parameter name/value pairs

---

### 3.4 validate_preconditions()

**Signature:**
```python
@abstractmethod
def validate_preconditions(self) -> tuple[bool, Optional[str]]:
    """Validate that event can execute successfully"""
    pass
```

**Purpose:** Checks all prerequisites before attempting simulation:
- Required data present and valid
- Teams/players exist
- Business rules satisfied

**Returns:** Tuple of `(is_valid, error_message)`
- `(True, None)` if valid
- `(False, "error description")` if invalid

**Example Implementation:**
```python
def validate_preconditions(self) -> tuple[bool, Optional[str]]:
    # Team ID validation
    if not (1 <= self.away_team_id <= 32):
        return False, f"Invalid away_team_id: {self.away_team_id}"

    if self.away_team_id == self.home_team_id:
        return False, "Teams must be different"

    # Week validation
    if self.week < 1 or self.week > 25:
        return False, f"Invalid week: {self.week}"

    return True, None
```

---

## 4. Optional Methods (Override as Needed)

### 4.1 _get_results()

**Signature:**
```python
def _get_results(self) -> Optional[Dict[str, Any]]:
    """Return results after event execution"""
    return None
```

**Purpose:** Returns output after simulation/execution. Optional - returns `None` if not yet executed.

**Caching Pattern:**
```python
def _get_results(self) -> Optional[Dict[str, Any]]:
    if not self._cached_result:
        return None

    return {
        "away_score": self._cached_result.data['away_score'],
        "home_score": self._cached_result.data['home_score'],
        "winner_id": self._cached_result.data.get('winner_id'),
        "simulated_at": self._cached_result.timestamp.isoformat()
    }
```

**Use Cases:**
- **GameEvent**: Scores, winner, statistics (cached after simulation)
- **ScoutingEvent**: Scouting reports (the primary value)
- **MediaEvent**: Generated article text

**Returns:** Dictionary of results, or `None` if not yet executed

---

### 4.2 _get_metadata()

**Signature:**
```python
def _get_metadata(self) -> Dict[str, Any]:
    """Return additional event metadata/context"""
    return {}
```

**Purpose:** Returns supplementary information that doesn't fit cleanly into parameters or results.

**Examples:**
```python
# GameEvent
def _get_metadata(self) -> Dict[str, Any]:
    return {
        "matchup_description": "DET @ GB",
        "is_playoff_game": False,
        "is_division_game": True
    }

# ScoutingEvent
def _get_metadata(self) -> Dict[str, Any]:
    return {
        "scouting_department": "College Scouting",
        "region": "National",
        "scout_quality": "elite"
    }
```

**Returns:** Dictionary of metadata (empty dict if no metadata)

---

### 4.3 get_game_id()

**Signature:**
```python
def get_game_id(self) -> str:
    """Return the game/context ID this event belongs to"""
    raise NotImplementedError(...)
```

**Purpose:** Returns identifier for grouping related events together.

**Use Cases:**
- Retrieving all events for a specific game/season/context
- Timeline/calendar organization
- Event filtering

**Examples:**
- `"game_20241215_22_at_23"` - Specific game
- `"season_2024_week_15"` - Week timeline
- `"scouting_general"` - General scouting context

**Default Behavior:** Raises `NotImplementedError` - subclasses must override

---

### 4.4 store_result()

**Signature:**
```python
def store_result(self, result: EventResult) -> None:
    """Store simulation result for caching"""
    self._cached_result = result
```

**Purpose:** Caches simulation result for future retrieval without re-simulation.

**Usage:**
```python
# After simulation
result = event.simulate()
event.store_result(result)  # Cache for later

# Later retrieval
if event._get_results():
    # Has cached results, can display without re-simulating
    print(f"Score: {event._get_results()['away_score']}")
```

---

### 4.5 to_database_format()

**Signature:**
```python
def to_database_format(self) -> Dict[str, Any]:
    """Convert event to database storage format"""
    return {
        "event_id": self.event_id,
        "event_type": self.get_event_type(),
        "timestamp": self.timestamp,
        "game_id": self.get_game_id(),
        "data": {
            "parameters": self._get_parameters(),
            "results": self._get_results(),
            "metadata": self._get_metadata()
        }
    }
```

**Purpose:** Converts event to Event Database API format with three-part structure.

**Default Implementation:** Uses template method pattern calling `_get_parameters()`, `_get_results()`, `_get_metadata()`.

**Can Override:** If custom database format needed (not recommended).

---

## 5. Data Structures

### EventResult

```python
@dataclass
class EventResult:
    """Standardized result from any event execution"""
    event_id: str
    event_type: str
    success: bool
    timestamp: datetime
    data: Dict[str, Any]
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "success": self.success,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "error_message": self.error_message
        }
```

**Fields:**
- `event_id`: Unique identifier matching event
- `event_type`: Type of event executed
- `success`: Whether execution succeeded
- `timestamp`: When execution completed
- `data`: Event-specific result data
- `error_message`: Error description if `success=False`

---

### EventMetadata

```python
@dataclass
class EventMetadata:
    """Optional metadata for events"""
    season: Optional[int] = None
    week: Optional[int] = None
    dynasty_id: Optional[str] = None
    tags: Optional[list[str]] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "season": self.season,
            "week": self.week,
            "dynasty_id": self.dynasty_id,
            "tags": self.tags,
            "notes": self.notes
        }
```

---

## 6. Implementation Patterns

### Pattern 1: Parameterized Event (GameEvent)

**Characteristics:**
- Has meaningful input parameters
- Can be scheduled before execution
- Results cached after simulation

**Implementation:**
```python
class GameEvent(BaseEvent):
    def __init__(self, away_team_id, home_team_id, week, game_date, ...):
        super().__init__()
        self.away_team_id = away_team_id
        self.home_team_id = home_team_id
        self.week = week
        self.game_date = game_date
        self._cached_result = None

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "away_team_id": self.away_team_id,
            "home_team_id": self.home_team_id,
            "week": self.week,
            "game_date": self.game_date.isoformat()
        }

    def _get_results(self) -> Optional[Dict[str, Any]]:
        if not self._cached_result:
            return None
        return {
            "away_score": self._cached_result.data['away_score'],
            "home_score": self._cached_result.data['home_score']
        }

    def simulate(self) -> EventResult:
        # Run game simulation
        simulator = FullGameSimulator(self.away_team_id, self.home_team_id)
        result = simulator.simulate_game(date=self.game_date)

        # Cache result
        event_result = EventResult(...)
        self._cached_result = event_result
        return event_result
```

**Workflow:**
```python
# 1. Create and schedule (parameters only)
game = GameEvent(away=22, home=23, week=15)
event_db.insert_event(game)  # Stores parameters, results=None

# 2. Later: retrieve and simulate
game = GameEvent.from_database(event_db.get_event_by_id(event_id))
result = game.simulate()  # Runs simulation, caches result

# 3. Update with cached results
event_db.update_event(game)  # Now has parameters + results
```

---

### Pattern 2: Result-Based Event (ScoutingEvent)

**Characteristics:**
- Minimal parameters
- Value is in the output (results)
- Execute immediately, store results

**Implementation:**
```python
class ScoutingEvent(BaseEvent):
    def __init__(self, scout_type, target_positions, ...):
        super().__init__()
        self.scout_type = scout_type
        self.target_positions = target_positions
        self._scouting_reports = None

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "scout_type": self.scout_type,
            "target_positions": self.target_positions
        }

    def _get_results(self) -> Optional[Dict[str, Any]]:
        if not self._scouting_reports:
            return None
        return {
            "scouting_reports": self._scouting_reports,
            "total_evaluated": len(self._scouting_reports)
        }

    def simulate(self) -> EventResult:
        # Generate scouting reports
        self._scouting_reports = self._generate_reports()

        return EventResult(
            event_id=self.event_id,
            event_type="SCOUTING",
            success=True,
            timestamp=datetime.now(),
            data={"scouting_reports": self._scouting_reports}
        )
```

**Workflow:**
```python
# 1. Execute immediately
scout = ScoutingEvent(scout_type="college", positions=["QB"])
result = scout.simulate()  # Generates reports

# 2. Store with results
event_db.insert_event(scout)  # Stores parameters + results together

# 3. Later: retrieve historical reports
scout = ScoutingEvent.from_database(event_db.get_event_by_id(event_id))
reports = scout._scouting_reports  # Historical data, not regenerated
```

---

## 7. Database Integration

### Storage Format

Events are stored in the `events` table with this structure:

```sql
CREATE TABLE events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    game_id TEXT NOT NULL,
    data TEXT NOT NULL  -- JSON
);
```

**JSON Data Field:**
```json
{
    "parameters": {
        "away_team_id": 22,
        "home_team_id": 23,
        "week": 15
    },
    "results": {
        "away_score": 24,
        "home_score": 21,
        "winner_id": 22
    },
    "metadata": {
        "is_playoff_game": false
    }
}
```

### EventDatabaseAPI Methods

```python
# Insert event
event_db.insert_event(event: BaseEvent) -> BaseEvent

# Insert multiple events (transaction)
event_db.insert_events(events: List[BaseEvent]) -> List[BaseEvent]

# Update event (add results after simulation)
event_db.update_event(event: BaseEvent) -> bool

# Retrieve by event ID
event_db.get_event_by_id(event_id: str) -> Optional[Dict[str, Any]]

# Retrieve all events for a game/context (polymorphic!)
event_db.get_events_by_game_id(game_id: str) -> List[Dict[str, Any]]

# Retrieve by event type
event_db.get_events_by_type(event_type: str) -> List[Dict[str, Any]]
```

---

## 8. Event Lifecycle

### Complete Event Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. EVENT CREATION                                           │
│    event = GameEvent(away=22, home=23, week=15)            │
│    - Initialize with parameters                             │
│    - Generate event_id                                      │
│    - Set timestamp                                          │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. VALIDATION                                               │
│    is_valid, error = event.validate_preconditions()        │
│    - Check parameters                                       │
│    - Validate business rules                                │
│    - Return (True, None) or (False, "error")               │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. STORAGE (Optional - can simulate first)                 │
│    event_db.insert_event(event)                            │
│    - Convert to database format                             │
│    - Store parameters (results=None initially)              │
│    - Enable scheduling for later execution                  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. EXECUTION                                                │
│    result = event.simulate()                               │
│    - Run event-specific logic                               │
│    - Generate results                                       │
│    - Cache results in event object                          │
│    - Return EventResult                                     │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. UPDATE (Optional - cache results in DB)                 │
│    event_db.update_event(event)                            │
│    - Store results alongside parameters                     │
│    - Enable historical queries without re-simulation        │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. RETRIEVAL                                                │
│    events = event_db.get_events_by_game_id("week_15")     │
│    - Polymorphic query (all event types)                    │
│    - Reconstruct event objects from database                │
│    - Access parameters and/or cached results                │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. Extension Guide

### Adding a New Event Type

**Step 1: Define Event Class**

```python
from events.base_event import BaseEvent, EventResult

class TradeEvent(BaseEvent):
    """Player/pick trade event"""

    def __init__(self, team1_id, team2_id, players_traded, picks_traded, ...):
        super().__init__()
        self.team1_id = team1_id
        self.team2_id = team2_id
        self.players_traded = players_traded
        self.picks_traded = picks_traded
        self._trade_result = None
```

**Step 2: Implement Required Methods**

```python
    def get_event_type(self) -> str:
        return "TRADE"

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "team1_id": self.team1_id,
            "team2_id": self.team2_id,
            "players_traded": self.players_traded,
            "picks_traded": self.picks_traded
        }

    def _get_results(self) -> Optional[Dict[str, Any]]:
        if not self._trade_result:
            return None
        return {
            "trade_successful": True,
            "cap_impact": self._trade_result['cap_impact'],
            "approval_status": "approved"
        }

    def simulate(self) -> EventResult:
        # Execute trade logic
        self._execute_trade()

        return EventResult(
            event_id=self.event_id,
            event_type="TRADE",
            success=True,
            timestamp=datetime.now(),
            data={"trade_details": self._trade_result}
        )

    def validate_preconditions(self) -> tuple[bool, Optional[str]]:
        # Validate trade is legal
        if self.team1_id == self.team2_id:
            return False, "Cannot trade with yourself"

        if not self.players_traded and not self.picks_traded:
            return False, "Must trade something"

        return True, None
```

**Step 3: Add Factory Method**

```python
    @classmethod
    def from_database(cls, event_data: Dict[str, Any]) -> 'TradeEvent':
        params = event_data['data']['parameters']

        trade = cls(
            team1_id=params['team1_id'],
            team2_id=params['team2_id'],
            players_traded=params['players_traded'],
            picks_traded=params['picks_traded']
        )

        # Restore results if available
        if 'results' in event_data['data'] and event_data['data']['results']:
            trade._trade_result = event_data['data']['results']

        return trade
```

**Step 4: Export in __init__.py**

```python
# src/events/__init__.py
from events.trade_event import TradeEvent

__all__ = [
    'BaseEvent',
    'GameEvent',
    'ScoutingEvent',
    'TradeEvent',  # Add new event type
    'EventDatabaseAPI',
]
```

---

## 10. Best Practices

### DO ✅

1. **Use Meaningful Event Types**
   ```python
   def get_event_type(self) -> str:
       return "GAME"  # Clear, uppercase, descriptive
   ```

2. **Cache Results After Simulation**
   ```python
   def simulate(self) -> EventResult:
       result = EventResult(...)
       self._cached_result = result  # Cache for _get_results()
       return result
   ```

3. **Validate Before Simulation**
   ```python
   is_valid, error = event.validate_preconditions()
   if not is_valid:
       print(f"Cannot simulate: {error}")
       return
   result = event.simulate()
   ```

4. **Handle Errors Gracefully**
   ```python
   def simulate(self) -> EventResult:
       try:
           # ... simulation logic ...
       except Exception as e:
           return EventResult(
               event_id=self.event_id,
               event_type=self.get_event_type(),
               success=False,
               error_message=str(e)
           )
   ```

5. **Store Appropriate Data Levels**
   - **Parameters**: Minimal for result-based events, complete for parameterized events
   - **Results**: Full for result-based events, summary for parameterized events
   - **Metadata**: Supplementary context that helps with filtering/display

### DON'T ❌

1. **Don't Store Redundant Data**
   ```python
   # BAD: Storing same data in parameters AND metadata
   def _get_parameters(self):
       return {"team_id": 22}

   def _get_metadata(self):
       return {"team_id": 22}  # Redundant!
   ```

2. **Don't Raise Exceptions in simulate()**
   ```python
   # BAD: Uncaught exception
   def simulate(self) -> EventResult:
       if invalid:
           raise ValueError("Bad data")  # Don't do this!

   # GOOD: Return error result
   def simulate(self) -> EventResult:
       if invalid:
           return EventResult(..., success=False, error_message="Bad data")
   ```

3. **Don't Forget Backward Compatibility**
   ```python
   # GOOD: Handle both old and new formats
   @classmethod
   def from_database(cls, event_data):
       if 'parameters' in event_data['data']:
           params = event_data['data']['parameters']  # New format
       else:
           params = event_data['data']  # Old format
   ```

4. **Don't Use get_event_type() for Business Logic**
   ```python
   # BAD: Type checking in business logic
   if event.get_event_type() == "GAME":
       # Do game-specific logic

   # GOOD: Use polymorphism
   result = event.simulate()  # Each event knows how to simulate itself
   ```

---

## 11. Testing Guidelines

### Unit Test Template

```python
import pytest
from events import GameEvent, EventDatabaseAPI

def test_event_creation():
    """Test event initializes correctly"""
    event = GameEvent(away_team_id=22, home_team_id=23, week=15)

    assert event.event_id is not None
    assert event.get_event_type() == "GAME"
    assert event.timestamp is not None

def test_event_validation():
    """Test precondition validation"""
    # Valid event
    event = GameEvent(away_team_id=22, home_team_id=23, week=15)
    is_valid, error = event.validate_preconditions()
    assert is_valid is True
    assert error is None

    # Invalid event (same teams)
    event = GameEvent(away_team_id=22, home_team_id=22, week=15)
    is_valid, error = event.validate_preconditions()
    assert is_valid is False
    assert "different" in error.lower()

def test_event_database_roundtrip():
    """Test store and retrieve"""
    event_db = EventDatabaseAPI(":memory:")
    event = GameEvent(away_team_id=22, home_team_id=23, week=15)

    # Store
    event_db.insert_event(event)

    # Retrieve
    retrieved = event_db.get_event_by_id(event.event_id)
    assert retrieved is not None
    assert retrieved['event_type'] == "GAME"
    assert retrieved['data']['parameters']['away_team_id'] == 22

def test_event_simulation_and_caching():
    """Test simulation caches results"""
    event = GameEvent(away_team_id=22, home_team_id=23, week=15)

    # Before simulation
    assert event._get_results() is None

    # Simulate
    result = event.simulate()
    assert result.success is True

    # After simulation
    assert event._get_results() is not None
    assert 'away_score' in event._get_results()
```

---

## 12. Performance Considerations

### Event Database Performance

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| `insert_event()` | O(log n) | Single write with index update |
| `insert_events()` | O(m log n) | Batch insert in transaction (10-50x faster) |
| `get_event_by_id()` | O(1) | Primary key lookup |
| `get_events_by_game_id()` | O(k) | k = events for that game, uses index |
| `update_event()` | O(log n) | Primary key update |

### Optimization Tips

1. **Use Batch Inserts**
   ```python
   # BAD: Multiple individual inserts
   for event in events:
       event_db.insert_event(event)

   # GOOD: Single batch insert
   event_db.insert_events(events)  # 10-50x faster
   ```

2. **Cache Results to Avoid Re-Simulation**
   ```python
   # Simulate once, cache in database
   result = event.simulate()
   event_db.update_event(event)  # Store results

   # Later: retrieve without re-simulating
   event = GameEvent.from_database(event_db.get_event_by_id(event_id))
   if event._get_results():
       # Use cached results, no simulation needed
       print(event._get_results()['away_score'])
   ```

3. **Use Appropriate game_id for Grouping**
   ```python
   # Good grouping for efficient queries
   game_id = "season_2024_week_15"  # Groups all week 15 events

   # Later: single query gets all week 15 events
   week_events = event_db.get_events_by_game_id("season_2024_week_15")
   ```

---

## 13. Future Enhancements

### Planned Features
- Event versioning for schema evolution
- Event dependencies (Event A must complete before Event B)
- Event replay/undo functionality
- Event archival for old seasons
- Event compression for storage efficiency

### Extension Points
- Custom serialization formats
- Event observers/listeners
- Event priority/scheduling
- Event conflict resolution

---

## 14. Related Documentation

- [Event Database API Specification](event_manager_api.md)
- [FullGameSimulator Specification](full_game_simulator.md)
- [Calendar Manager Plan](../plans/calendar_manager_plan.md)

---

## 15. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-10-02 | Initial specification with basic event interface |
| 1.1.0 | 2025-10-02 | Added three-part structure (parameters/results/metadata), ScoutingEvent pattern |

---

**Document Control**
- Author: System Architect
- Reviewers: Development Team
- Status: Implemented and Tested