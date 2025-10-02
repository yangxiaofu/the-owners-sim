# Calendar Component - Design Specification

## Component Overview

**Name:** `CalendarComponent`  
**Responsibility:** Maintain and advance the game's date/time state  
**Scope:** Single source of truth for the current date in the simulation

## Core Responsibility

The Calendar Component manages the current date in the game simulation and provides the ability to advance time forward by a specified number of days.

---

## Public Interface

### Primary Method

```
advance(days: integer) -> DateAdvanceResult
```

**Parameters:**
- `days` (integer): Number of days to advance (must be positive)

**Returns:**
- `DateAdvanceResult` object containing:
  - `startDate`: Date before advancement
  - `endDate`: Date after advancement
  - `daysAdvanced`: Actual number of days advanced
  - `eventsTriggered`: List of date-based events that occurred
  - `transitionsCrossed`: List of transitions (season end, year end, etc.)

**Throws:**
- `InvalidDaysException`: If days ≤ 0
- `SeasonCompletedException`: If advancing beyond defined season end without proper handling

### Query Methods

```
getCurrentDate() -> Date
getCurrentSeason() -> integer (year)
getCurrentWeek() -> integer (1-18 for NFL season)
getSeasonDay() -> integer (day within current season)
isOffseason() -> boolean
isDuringRegularSeason() -> boolean
isDuringPlayoffs() -> boolean
getNextMilestone() -> DateMilestone (next significant date)
```

### Configuration Methods

```
setStartDate(date: Date) -> void
setSeasonStructure(structure: SeasonStructure) -> void
reset() -> void
```

---

## Internal State

### Core State
```
currentDate: Date
seasonStartDate: Date
seasonEndDate: Date
offseasonStartDate: Date
```

### Configuration State
```
seasonStructure: SeasonStructure
  - regularSeasonWeeks: integer (17)
  - preseasonWeeks: integer (4)
  - playoffWeeks: integer (4)
  - offseasonWeeks: integer (27)
```

### Derived State (Calculated, not stored)
```
currentWeek: calculated from currentDate
currentPhase: PRESEASON | REGULAR_SEASON | PLAYOFFS | OFFSEASON
daysUntilNextPhase: calculated
```

---

## Data Structures

### Date Object
```
{
  year: integer
  month: integer (1-12)
  day: integer (1-31)
}
```

### DateAdvanceResult
```
{
  startDate: Date
  endDate: Date
  daysAdvanced: integer
  eventsTriggered: Event[]
  transitionsCrossed: Transition[]
}
```

### SeasonPhase Enum
```
PRESEASON
REGULAR_SEASON
PLAYOFFS
OFFSEASON
```

### Transition Object
```
{
  type: TransitionType (SEASON_START, SEASON_END, YEAR_END, PHASE_CHANGE)
  date: Date
  fromPhase: SeasonPhase (nullable)
  toPhase: SeasonPhase (nullable)
}
```

---

## Behavior Specifications

### Advancing Calendar

**Standard Advancement:**
1. Validate `days` parameter (must be > 0)
2. Calculate new date (currentDate + days)
3. Identify any phase transitions crossed
4. Identify any milestone dates crossed
5. Update currentDate
6. Return DateAdvanceResult

**Phase Transitions:**
- When crossing from Regular Season → Playoffs
- When crossing from Playoffs → Offseason
- When crossing from Offseason → Preseason
- When crossing from Preseason → Regular Season

**Year Rollover:**
- Handle December 31 → January 1 transition
- Increment year counter
- No special logic needed beyond standard date arithmetic

---

## Constraints and Validation

### Input Constraints
- `days` must be > 0
- `days` should have a reasonable maximum (e.g., 365) to prevent accidental skips
- Cannot advance to a date beyond the configured season boundary without explicit permission

### State Invariants
- `currentDate` must always be valid
- `currentDate` must be >= `seasonStartDate`
- `currentDate` must be <= `seasonEndDate` during active season
- Phase transitions must follow logical sequence

### Edge Cases
- Advancing exactly to a transition date
- Advancing over multiple transitions in one call
- Advancing during offseason
- Leap years
- Advancing by very large numbers (should fail gracefully or warn)

---

## Dependencies

### Required Dependencies
- **DateUtils**: Library for date arithmetic and validation
  - Methods: addDays(), compareDates(), isValidDate()

### Optional Dependencies
- **EventSystem**: For publishing date change events (publish/subscribe pattern)
- **LoggingService**: For audit trail of date changes

### Consumers (Systems that depend on Calendar)
- GameStateManager (coordinates overall simulation)
- ScheduleComponent (uses dates for games)
- ContractComponent (checks expiration dates)
- InjuryComponent (tracks injury durations)
- ScoutingComponent (season-dependent scouting windows)
- DraftComponent (triggered by specific dates)

---

## Events & Notifications

### Published Events

The Calendar Component should publish events when significant transitions occur:

```
EVENT: DateAdvanced
  data: { startDate, endDate, daysAdvanced }

EVENT: PhaseTransition
  data: { fromPhase, toPhase, transitionDate }

EVENT: SeasonStarted
  data: { season, startDate }

EVENT: SeasonEnded
  data: { season, endDate }

EVENT: MilestoneReached
  data: { milestoneType, date, description }
```

---

## Configuration

### Initial Setup
```
defaultSeasonStart: August 1st
defaultOffseasonStart: February 15th
configurable: true (allow custom seasons)
```

### Season Structure Template
```
NFL Standard Season:
  - Preseason Start: Early August
  - Regular Season Start: Early September (Week 1)
  - Regular Season End: Early January (Week 18)
  - Playoffs: January
  - Super Bowl: Mid-February
  - Offseason: Mid-February through July
  - Draft: Late April
  - Free Agency: March
```

---

## Testing Strategy

### Unit Tests
- ✓ Advance by 1 day
- ✓ Advance by multiple days
- ✓ Advance across week boundary
- ✓ Advance across month boundary
- ✓ Advance across year boundary
- ✓ Advance across phase transition
- ✓ Advance with invalid input (negative, zero, too large)
- ✓ Advance beyond season end
- ✓ Multiple transitions in single advance

### Integration Tests
- ✓ Calendar advance triggers game simulation
- ✓ Calendar advance updates contract expirations
- ✓ Calendar advance triggers scheduled events
- ✓ Calendar state persists correctly

### Edge Case Tests
- ✓ Leap year handling
- ✓ Advance by 365+ days
- ✓ Reset and re-initialize
- ✓ Concurrent advance calls (thread safety if applicable)

---

## Performance Considerations

### Targets
- `advance()` should complete in < 1ms for typical calls (1-7 days)
- `getCurrentDate()` should be O(1)
- Memory footprint: < 1KB for state

### Optimization Notes
- Cache calculated values (currentWeek, currentPhase) if queried frequently
- Use efficient date library (avoid heavy frameworks)
- Minimize event publishing overhead

---

## Error Handling

### Error Scenarios
```
InvalidDaysException
  - When: days <= 0
  - Recovery: Reject operation, maintain current state

SeasonBoundaryException
  - When: Advancing beyond configured season end
  - Recovery: Either auto-rollover or require explicit confirmation

InvalidDateException
  - When: Date calculation results in invalid date
  - Recovery: Should never happen with proper date library; fail fast if it does
```

---

## Persistence

### Save State
```
{
  currentDate: Date
  seasonStartDate: Date
  seasonEndDate: Date
  seasonStructure: SeasonStructure
}
```

### Load State
- Validate loaded dates
- Recalculate derived state
- Verify phase consistency

---

## Future Enhancements (Out of Scope for v1)

- Multiple calendar views (fiscal year vs. season year)
- Historical date tracking/audit log
- Ability to reverse time (undo)
- Calendar speed multipliers (advance at 2x, 3x speed)
- Pause/resume mechanics
- Scheduled automated advancements
- International season support

---

## Integration Points

### With Other Components

**GameStateManager → Calendar**
- Calls `advance()` to progress simulation
- Queries current date for save state

**Calendar → EventSystem**
- Publishes date change events
- Publishes phase transition events

**ScheduleComponent → Calendar**
- Queries `getCurrentDate()` to determine active games
- Subscribes to date advancement events

**ContractComponent → Calendar**
- Queries date to check contract expirations
- Subscribes to offseason start events

---

## Implementation Notes

### Recommended Approach
1. Start with simple Date object (year, month, day)
2. Implement basic advance() with validation
3. Add phase calculation logic
4. Add transition detection
5. Implement event publishing
6. Add persistence
7. Optimize based on performance metrics

### Anti-Patterns to Avoid
- ❌ Don't make Calendar responsible for triggering game simulations
- ❌ Don't store redundant date information in multiple places
- ❌ Don't allow direct manipulation of currentDate (only through advance())
- ❌ Don't couple Calendar to specific game rules (keep it domain-agnostic where possible)

---

## Success Criteria

The Calendar Component is complete when:
- ✓ Can reliably advance by any positive number of days
- ✓ Correctly identifies and reports phase transitions
- ✓ Maintains accurate date state
- ✓ Integrates cleanly with GameStateManager
- ✓ Passes all unit and integration tests
- ✓ Performance targets are met
- ✓ State can be saved and loaded correctly