# Event Database API - Component Specification

**Version:** 1.0  
**Last Updated:** 2025-10-02  
**Status:** Draft

---

## 1. Overview

### Purpose
Generic persistence layer for storing and retrieving game events. This component provides database operations without knowledge of event types or game logic.

### Scope
- Insert single or multiple events
- Retrieve events by ID or game ID
- Handle database transactions and connections

### Non-Goals
- Event validation or business rules
- Event type definitions or schemas
- Event processing or interpretation
- ID or timestamp generation

---

## 2. Component Interface

### Public API

```typescript
interface EventDatabaseAPI {
  // Create Operations
  insertEvent(event: GameEvent): Promise<GameEvent>;
  insertEvents(events: GameEvent[]): Promise<GameEvent[]>;
  
  // Read Operations
  getEventById(eventId: string): Promise<GameEvent | null>;
  getEventsByGameId(gameId: string): Promise<GameEvent[]>;
}
```

---

## 3. Data Model

### GameEvent Type

```typescript
interface GameEvent {
  // Identity
  event_id: string;              // UUID (provided by caller)
  event_type: string;            // Arbitrary string label
  
  // Timing
  timestamp: Date;               // When event occurred
  
  // Context
  game_id: string;               // Game identifier for filtering
  
  // Event Data
  data: Record<string, any>;     // Flexible JSON object
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_id` | string | Yes | Unique identifier (UUID format recommended) |
| `event_type` | string | Yes | Label identifying event type (e.g., "TOUCHDOWN") |
| `timestamp` | Date | Yes | Real-world time when event occurred |
| `game_id` | string | Yes | Game this event belongs to |
| `data` | object | Yes | Flexible JSON containing event-specific details |

---

## 4. Database Schema

### Table: events

```sql
CREATE TABLE events (
  event_id VARCHAR(36) PRIMARY KEY,
  event_type VARCHAR(100) NOT NULL,
  timestamp BIGINT NOT NULL,
  game_id VARCHAR(36) NOT NULL,
  data TEXT NOT NULL
);

CREATE INDEX idx_game_id ON events(game_id);
CREATE INDEX idx_timestamp ON events(timestamp);
```

### Schema Notes
- `timestamp` stored as Unix timestamp (milliseconds since epoch)
- `data` stored as JSON text
- Primary key on `event_id` for fast single-record lookup
- Index on `game_id` for filtering events by game
- Index on `timestamp` for chronological ordering

---

## 5. Method Specifications

### insertEvent

**Purpose:** Insert a single event into the database.

**Signature:**
```typescript
async insertEvent(event: GameEvent): Promise<GameEvent>
```

**Parameters:**
- `event` (GameEvent): Event object to store

**Returns:**
- Promise resolving to the inserted event

**Behavior:**
- Inserts event into database
- Returns original event object on success
- Throws error if database operation fails

**Example:**
```typescript
const event = {
  event_id: 'evt-123',
  event_type: 'TOUCHDOWN',
  timestamp: new Date(),
  game_id: 'game-456',
  data: { player: 'Player 1', yards: 45 }
};

await eventDB.insertEvent(event);
```

---

### insertEvents

**Purpose:** Insert multiple events in a single transaction for performance.

**Signature:**
```typescript
async insertEvents(events: GameEvent[]): Promise<GameEvent[]>
```

**Parameters:**
- `events` (GameEvent[]): Array of event objects to store

**Returns:**
- Promise resolving to array of inserted events

**Behavior:**
- Wraps all inserts in a database transaction
- All inserts succeed or all fail (atomic operation)
- Rolls back transaction on any error
- Significantly faster than multiple `insertEvent` calls

**Example:**
```typescript
const events = [
  { event_id: 'e1', event_type: 'TOUCHDOWN', timestamp: new Date(), game_id: 'g1', data: {} },
  { event_id: 'e2', event_type: 'FIELD_GOAL', timestamp: new Date(), game_id: 'g1', data: {} },
  { event_id: 'e3', event_type: 'INJURY', timestamp: new Date(), game_id: 'g1', data: {} }
];

await eventDB.insertEvents(events);
```

---

### getEventById

**Purpose:** Retrieve a specific event by its ID.

**Signature:**
```typescript
async getEventById(eventId: string): Promise<GameEvent | null>
```

**Parameters:**
- `eventId` (string): Unique identifier of the event

**Returns:**
- Promise resolving to GameEvent if found, null if not found

**Behavior:**
- Queries database for event with matching ID
- Deserializes JSON data field
- Returns null if event doesn't exist (not an error)

**Example:**
```typescript
const event = await eventDB.getEventById('evt-123');
if (event) {
  console.log(event.event_type, event.data);
}
```

---

### getEventsByGameId

**Purpose:** Retrieve all events for a specific game, ordered chronologically.

**Signature:**
```typescript
async getEventsByGameId(gameId: string): Promise<GameEvent[]>
```

**Parameters:**
- `gameId` (string): Identifier of the game

**Returns:**
- Promise resolving to array of GameEvent objects (empty array if none found)

**Behavior:**
- Queries database for all events with matching game_id
- Results ordered by timestamp ascending (oldest first)
- Deserializes JSON data field for each event
- Returns empty array if no events found (not an error)

**Example:**
```typescript
const events = await eventDB.getEventsByGameId('game-456');
console.log(`Game has ${events.length} events`);

for (const event of events) {
  console.log(`${event.timestamp}: ${event.event_type}`);
}
```

---

## 6. Implementation Details

### Constructor

```typescript
constructor(databasePath: string)
```

**Parameters:**
- `databasePath`: File path to SQLite database (use ':memory:' for in-memory)

**Behavior:**
- Opens or creates SQLite database at specified path
- Initializes schema (creates tables and indexes if they don't exist)
- Ready for use after construction

---

### Error Handling

**General Principles:**
- All methods throw errors on database failures
- Callers should wrap calls in try-catch blocks
- Use transactions for batch operations to ensure atomicity

**Error Scenarios:**
- Database connection failure
- SQL syntax errors (shouldn't happen with parameterized queries)
- Constraint violations (duplicate event_id)
- Disk full or permissions issues

---

### Performance Characteristics

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| `insertEvent` | O(log n) | Single write with index update |
| `insertEvents` | O(m log n) | m = batch size, transactional |
| `getEventById` | O(1) | Primary key lookup |
| `getEventsByGameId` | O(k) | k = events for that game, index scan |

**Batch Insert Performance:**
- Inserting 100 events individually: ~100 transactions
- Inserting 100 events with `insertEvents`: 1 transaction (10-50x faster)

---

## 7. Usage Examples

### Basic Usage

```typescript
// Initialize
const eventDB = new EventDatabaseAPI('./game_data/events.db');

// Store single event
await eventDB.insertEvent({
  event_id: generateUUID(),
  event_type: 'GAME_START',
  timestamp: new Date(),
  game_id: 'game-123',
  data: { home_team: 'Team A', away_team: 'Team B' }
});

// Retrieve all game events
const events = await eventDB.getEventsByGameId('game-123');
```

### Integration with Game Simulation

```typescript
class GameSimulation {
  constructor(private eventDB: EventDatabaseAPI) {}
  
  async simulateGame(gameId: string) {
    const events: GameEvent[] = [];
    
    // Simulate plays and create events
    for (let i = 0; i < 150; i++) {
      events.push({
        event_id: generateUUID(),
        event_type: this.determinePlayType(),
        timestamp: new Date(),
        game_id: gameId,
        data: this.generatePlayData()
      });
    }
    
    // Store all events at once
    await this.eventDB.insertEvents(events);
  }
  
  async generateRecap(gameId: string) {
    const events = await this.eventDB.getEventsByGameId(gameId);
    
    // Process events to create game summary
    const touchdowns = events.filter(e => e.event_type === 'TOUCHDOWN');
    const fieldGoals = events.filter(e => e.event_type === 'FIELD_GOAL');
    
    return {
      total_plays: events.length,
      touchdowns: touchdowns.length,
      field_goals: fieldGoals.length
    };
  }
}
```

---

## 8. Testing

### Unit Test Coverage

```typescript
describe('EventDatabaseAPI', () => {
  let db: EventDatabaseAPI;
  
  beforeEach(() => {
    db = new EventDatabaseAPI(':memory:');
  });
  
  test('stores and retrieves event', async () => {
    const event = createTestEvent();
    await db.insertEvent(event);
    const retrieved = await db.getEventById(event.event_id);
    expect(retrieved).toEqual(event);
  });
  
  test('batch insert is atomic', async () => {
    const events = createTestEvents(100);
    await db.insertEvents(events);
    const retrieved = await db.getEventsByGameId(events[0].game_id);
    expect(retrieved).toHaveLength(100);
  });
  
  test('filters by game_id correctly', async () => {
    await db.insertEvent(createTestEvent({ game_id: 'game-1' }));
    await db.insertEvent(createTestEvent({ game_id: 'game-2' }));
    
    const game1Events = await db.getEventsByGameId('game-1');
    expect(game1Events).toHaveLength(1);
  });
  
  test('returns null for non-existent event', async () => {
    const event = await db.getEventById('non-existent');
    expect(event).toBeNull();
  });
  
  test('returns empty array for game with no events', async () => {
    const events = await db.getEventsByGameId('non-existent-game');
    expect(events).toEqual([]);
  });
});
```

### Performance Tests

```typescript
test('batch insert performance', async () => {
  const events = createTestEvents(1000);
  
  const start = Date.now();
  await db.insertEvents(events);
  const duration = Date.now() - start;
  
  expect(duration).toBeLessThan(1000); // Should complete in < 1 second
});

test('query performance with large dataset', async () => {
  const events = createTestEvents(10000);
  await db.insertEvents(events);
  
  const start = Date.now();
  await db.getEventsByGameId(events[0].game_id);
  const duration = Date.now() - start;
  
  expect(duration).toBeLessThan(100); // Should be fast with index
});
```

---

## 9. Dependencies

### Runtime Dependencies
- SQLite database engine (or compatible)
- Database driver (e.g., `better-sqlite3`, `sqlite3`)

### Development Dependencies
- Testing framework (Jest, Mocha, etc.)
- TypeScript compiler

---

## 10. Component Boundaries

### What This Component Owns
- Database schema for events table
- CRUD operations on events
- Transaction management for batch operations
- Data serialization/deserialization (JSON)

### What This Component Does NOT Own
- Event type definitions (owned by Game Simulation)
- Event validation rules (owned by Game Simulation)
- Event interpretation (owned by Game Simulation)
- Statistics calculation from events (owned by Stats System)
- ID generation (caller responsibility)

---

## 11. Future Enhancements

### Possible Additions
- Delete operations (for admin/testing)
- Query by date range
- Query by event type
- Event count by game
- Pagination for large result sets
- Archive/compress old events

### Not Planned
- Complex event filtering (use separate query layer)
- Event processing or handlers
- Real-time event streaming
- Event validation

---

## 12. Configuration

### Database Configuration

```typescript
interface DatabaseConfig {
  path: string;                  // Database file path
  timeout?: number;              // Query timeout in milliseconds
  readonly?: boolean;            // Open in read-only mode
}

// Example
const config = {
  path: './game_data/events.db',
  timeout: 5000,
  readonly: false
};
```

---

## 13. Migration & Versioning

### Schema Versioning
Current version: 1.0

### Future Schema Changes
If schema changes are needed:
1. Add version tracking table
2. Include migration scripts
3. Support reading old schema format
4. Provide upgrade path

---

## 14. Architecture Diagram

```
┌─────────────────────────────────────┐
│     Game Simulation Component       │
│  - Creates events                   │
│  - Defines event structure          │
│  - Interprets events                │
└─────────────┬───────────────────────┘
              │
              │ insertEvents()
              │ getEventsByGameId()
              │
              ▼
┌─────────────────────────────────────┐
│     Event Database API              │
│  - insertEvent()                    │
│  - insertEvents()                   │
│  - getEventById()                   │
│  - getEventsByGameId()              │
└─────────────┬───────────────────────┘
              │
              │ SQL queries
              │
              ▼
┌─────────────────────────────────────┐
│     SQLite Database                 │
│  - events table                     │
│  - indexes                          │
└─────────────────────────────────────┘
```

---

## 15. Acceptance Criteria

### Ready for Implementation When:
- [x] Interface is defined
- [x] Data model is specified
- [x] Database schema is designed
- [x] Method behaviors are documented
- [x] Error handling is specified

### Ready for Production When:
- [ ] All methods implemented
- [ ] Unit tests pass (>90% coverage)
- [ ] Performance tests pass
- [ ] Integration tests with Game Simulation pass
- [ ] Documentation complete
- [ ] Code review approved

---

## Appendix A: SQL Reference

### Create Table
```sql
CREATE TABLE events (
  event_id VARCHAR(36) PRIMARY KEY,
  event_type VARCHAR(100) NOT NULL,
  timestamp BIGINT NOT NULL,
  game_id VARCHAR(36) NOT NULL,
  data TEXT NOT NULL
);
```

### Create Indexes
```sql
CREATE INDEX idx_game_id ON events(game_id);
CREATE INDEX idx_timestamp ON events(timestamp);
```

### Common Queries
```sql
-- Insert event
INSERT INTO events (event_id, event_type, timestamp, game_id, data)
VALUES (?, ?, ?, ?, ?);

-- Get by ID
SELECT * FROM events WHERE event_id = ?;

-- Get by game
SELECT * FROM events WHERE game_id = ? ORDER BY timestamp ASC;
```

---

## Appendix B: Example Event Structures

These examples show how the Game Simulation component might structure events. The Event Database API doesn't enforce these structures.

### Touchdown Event
```json
{
  "event_id": "evt-abc123",
  "event_type": "TOUCHDOWN",
  "timestamp": "2024-10-02T14:23:45.000Z",
  "game_id": "game-xyz789",
  "data": {
    "team_id": "team-1",
    "player_id": "player-42",
    "yards": 45,
    "quarter": 3,
    "game_clock": "8:23",
    "play_type": "passing"
  }
}
```

### Injury Event
```json
{
  "event_id": "evt-def456",
  "event_type": "INJURY",
  "timestamp": "2024-10-02T14:28:12.000Z",
  "game_id": "game-xyz789",
  "data": {
    "player_id": "player-17",
    "injury_type": "KNEE",
    "severity": "MODERATE",
    "estimated_recovery_weeks": 6
  }
}
```

---

**Document Control**
- Author: AI Assistant
- Reviewers: [To be assigned]
- Approval: [Pending]