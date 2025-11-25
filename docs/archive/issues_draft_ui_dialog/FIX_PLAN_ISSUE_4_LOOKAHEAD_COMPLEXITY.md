# Fix Plan: Issue #4 - Look-Ahead Pattern Complexity

**Priority**: LOW
**Complexity**: Medium-High
**Estimated Time**: 12-16 hours (3-4 days)
**Risk Level**: HIGH
**Recommendation**: **DEFER** - Cost-benefit ratio unfavorable

## Problem Statement

### Current Behavior
The system uses a "look-ahead" pattern where it checks TOMORROW's date for milestones before simulating TODAY:

```python
# Current pattern: Check TOMORROW before simulating TODAY
def advance_week(self) -> Dict[str, Any]:
    for day_num in range(7):
        # Look ahead to tomorrow
        next_date = self._get_next_date()

        if self._check_for_milestone_on_next_date(next_date):
            # Stop BEFORE simulating today
            return {'milestone_on': next_date}

        # Simulate today
        self._simulate_day()
```

### Impact
- **Mental Model Confusion**: Developers must think "one day ahead"
- **Temporal Misalignment**: Checking tomorrow's event before today finishes
- **Code Complexity**: Off-by-one errors in date calculations
- **Testing Difficulty**: Test data setup requires +1 day thinking
- **Debugging Confusion**: Logs show "checking April 24" while calendar shows "April 23"

### Why This Pattern Exists
The look-ahead pattern serves a specific purpose:

1. **User Control**: User wants to control what happens ON milestone day
2. **Stop-Before Logic**: Must stop simulation BEFORE milestone day arrives
3. **UI Routing**: Need to launch dialog when milestone day arrives (not after it's gone)

**Example**: Draft Day is April 24
- Simulation STOPS on April 23 (day before)
- User advances to April 24 manually
- Dialog launches for April 24
- User controls draft experience

If we simulated April 24 automatically, user would miss the interactive event.

## Solution Analysis

### Option A: Same-Day Check (Naive Refactor) ❌ DOESN'T WORK

**Approach**: Check today instead of tomorrow
```python
def advance_week(self):
    for day_num in range(7):
        self._simulate_day()  # Simulate first

        if self._check_for_milestone_on_current_date():
            # Stop AFTER simulating milestone day
            return {'milestone_on': current_date}
```

**Problems**:
- ❌ **Already Simulated Milestone Day**: By the time we detect it, day is gone
- ❌ **No User Control**: Draft day auto-simulates before user can interact
- ❌ **Dialog Too Late**: User sees April 25 but dialog says "Draft Day April 24"
- ❌ **Breaks Core Requirement**: User must be stopped BEFORE milestone, not after

**Verdict**: Doesn't solve the user experience problem.

### Option B: Event Subscription System (Complex) ⚠️ OVERKILL

**Approach**: Calendar publishes events, simulation subscribes
```python
class CalendarEventBus:
    def subscribe(self, event_type: EventType, handler: Callable):
        """Subscribe to future events."""
        pass

    def publish_upcoming_events(self, days_ahead: int):
        """Notify subscribers of upcoming events."""
        pass

# In SimulationController
def __init__(self):
    calendar.subscribe(EventType.DRAFT_DAY, self._on_draft_day_approaching)

def _on_draft_day_approaching(self, event_date: str):
    """Called when draft day is 1 day away."""
    self._stop_simulation_before_date(event_date)
```

**Pros**:
- ✅ Decouples milestone detection from simulation
- ✅ More extensible for future event types

**Cons**:
- ❌ **High Complexity**: Pub/sub system, event registration, lifecycle management
- ❌ **Over-Engineering**: Solves problem we don't have (only 2-3 milestone types)
- ❌ **Still Has Look-Ahead**: Need to check "tomorrow" to fire "approaching" event
- ❌ **Testing Overhead**: Mock event bus, verify subscriptions, etc.
- ❌ **12-16 hour implementation**: Not justified for minor code clarity improvement

**Verdict**: Technically sound but massive overkill.

### Option C: Explicit "Stop-Before" API (Better) ⚙️ MODERATE COMPLEXITY

**Approach**: Make look-ahead pattern explicit in API
```python
class MilestoneChecker:
    def should_stop_before_date(self, date: str) -> Optional[Milestone]:
        """
        Check if simulation should stop BEFORE reaching this date.
        Returns milestone if one exists ON this date (not before it).
        """
        # Check if date has milestone
        milestone = self._get_milestone_on_date(date)

        if milestone and milestone.requires_user_interaction:
            return milestone

        return None

# In simulation loop
def advance_week(self):
    for day_num in range(7):
        # Explicit: Check if we should stop before tomorrow
        next_date = self._calendar.get_next_date()
        milestone = self._milestone_checker.should_stop_before_date(next_date)

        if milestone:
            # STOP - don't simulate today, milestone is tomorrow
            return {'stop_reason': 'milestone_tomorrow', 'milestone_date': next_date}

        # Safe to simulate today
        self._simulate_day()
```

**Pros**:
- ✅ Explicit in method name: "should_stop_BEFORE"
- ✅ Clear semantics: returns milestone ON the date, not before it
- ✅ Better documentation: Method name explains behavior
- ✅ Easier testing: Mock `should_stop_before_date()` with clear contract

**Cons**:
- ❌ Still conceptually look-ahead (just more explicit)
- ❌ Refactoring effort across multiple files
- ❌ Doesn't eliminate off-by-one confusion, just names it better

**Verdict**: Incremental improvement but doesn't fundamentally solve problem.

### Option D: Keep Current Pattern + Better Documentation ✅ RECOMMENDED

**Approach**: Accept pattern as inherent to problem domain, improve clarity

**Changes**:
1. Add comprehensive docstrings explaining why
2. Rename variables for clarity
3. Add diagram to architecture docs
4. Add helper method with clear name
5. Add unit test demonstrating pattern

**Implementation**:
```python
def advance_week(self) -> Dict[str, Any]:
    """
    Simulate up to 7 days, stopping if interactive milestone is TOMORROW.

    Look-Ahead Pattern Rationale:
    We check TOMORROW for milestones to stop BEFORE the milestone day.
    This allows user to control what happens ON the milestone day.

    Example: Draft Day is April 24
        - We simulate April 23
        - We check April 24 (tomorrow) for milestones
        - We find Draft Day milestone
        - We STOP (don't simulate April 24)
        - User advances to April 24 manually
        - Draft dialog launches for April 24

    This pattern is intentional and necessary for interactive events.
    """
    for day_num in range(7):
        # Look ahead: Check if TOMORROW has interactive milestone
        tomorrow_date = self._get_next_date()

        if self._has_interactive_milestone_on_date(tomorrow_date):
            logger.info(
                f"Stopping simulation before {tomorrow_date} "
                f"(milestone detected). Current date: {self._current_date}"
            )
            return {
                'stopped_before_milestone': True,
                'milestone_date': tomorrow_date,
                'current_date': self._current_date
            }

        # Safe to simulate today (no milestone tomorrow)
        self._simulate_day()

    return {'completed': True, 'days_simulated': 7}
```

**Documentation Addition** (`docs/architecture/milestone_detection_pattern.md`):
```markdown
# Milestone Detection: Look-Ahead Pattern

## Why Check Tomorrow Instead of Today?

The simulation uses a "look-ahead" pattern where it checks TOMORROW's date
for milestones before simulating TODAY. This seems counterintuitive but is
essential for interactive event handling.

### Problem We're Solving

User must be able to control what happens ON milestone days (e.g., Draft Day).
If we auto-simulate the milestone day, user misses the interactive experience.

### Pattern

┌─────────────────────────────────────────────────────────┐
│  Simulation Loop                                        │
│                                                         │
│  Current Date: April 23                                │
│                                                         │
│  1. Check Tomorrow (April 24) for milestones           │
│     → Draft Day Found on April 24                      │
│                                                         │
│  2. STOP simulation (don't simulate April 23)          │
│     → Prevents auto-advancing to April 24              │
│                                                         │
│  3. User sees "April 23" in UI                         │
│     → User clicks "Advance Day"                        │
│                                                         │
│  4. UI advances to April 24                            │
│     → Draft dialog launches                            │
│                                                         │
│  5. User controls draft experience                     │
│                                                         │
└─────────────────────────────────────────────────────────┘

### Alternative Considered: Check Today

If we checked TODAY instead of TOMORROW:

Current Date: April 24 (Draft Day)
1. Simulate April 24 ← Auto-simulates draft day
2. Check April 24 for milestone ← Too late! Day already simulated
3. Launch dialog ← But draft already happened

Result: User has no control, draft auto-completed.

### Mental Model

Think of it as a "stop sign": The stop sign is BEFORE the intersection,
not AT the intersection. We check for the stop sign (milestone) before
entering the intersection (simulating the day).

### Code Implications

When working with milestone detection:
- Always think "stop BEFORE milestone day"
- Milestone date is TOMORROW, not TODAY
- Use variable names like `next_date`, `tomorrow_date` for clarity
- Log both current date and milestone date for debugging
```

**Pros**:
- ✅ **Zero Refactoring**: No code changes, zero risk
- ✅ **Preserves Correctness**: Current pattern works perfectly
- ✅ **Low Cost**: 2-3 hours for docs + tests
- ✅ **Educational**: New developers learn pattern once, understand forever
- ✅ **Pragmatic**: Accepts inherent complexity of problem domain

**Cons**:
- ❌ Doesn't eliminate mental model mismatch
- ❌ Still requires "+1 day" thinking in some places

**Verdict**: Best cost-benefit ratio. Accept complexity, document well.

## Recommendation: DEFER (Option D as Minimal Fix)

### Analysis
This issue stems from inherent problem domain complexity, not poor code design. The look-ahead pattern is the CORRECT solution for the requirement "stop before milestone day." Any attempt to "simplify" it either:
1. Breaks user experience (Option A)
2. Adds massive complexity (Option B)
3. Renames without fixing (Option C)

### Cost-Benefit Analysis

| Approach | Time | Risk | Benefit |
|----------|------|------|---------|
| Option A: Same-day check | 4h | HIGH | ❌ Breaks UX |
| Option B: Event bus | 16h | MEDIUM | ⚠️ Over-engineered |
| Option C: Explicit API | 8h | LOW | 🔶 Marginal clarity |
| **Option D: Document** | **2h** | **NONE** | **✅ Sufficient** |

### Recommendation
**Implement Option D only** (2 hours):
1. Add comprehensive docstrings to `_check_for_milestone_on_next_date()`
2. Create architecture doc explaining pattern
3. Add unit test demonstrating pattern
4. Update variable names for clarity (`next_date` instead of `date`)

**Defer full refactor** until:
- We have 5+ milestone types (currently only 2-3)
- Multiple developers report confusion (currently hypothetical)
- User experience requires more complex event orchestration

### Minimal Implementation (Option D)

#### Phase 1: Code Documentation (1 hour)

**File**: `src/season/season_cycle_controller.py`

```python
def _check_for_milestone_on_next_date(self, next_date: str) -> Optional[Dict]:
    """
    Check if NEXT date (tomorrow) has an interactive milestone.

    IMPORTANT: This is a "look-ahead" check. We check TOMORROW's date
    to decide if we should STOP BEFORE reaching tomorrow.

    Rationale:
        Interactive milestones (Draft Day, Trade Deadline) require user
        control. We must stop simulation BEFORE the milestone day arrives,
        allowing user to trigger it manually. If we checked TODAY instead,
        we'd auto-simulate the milestone day before user could interact.

    Example:
        Current date: April 23
        next_date parameter: April 24 (Draft Day)

        Return value: {'type': 'DRAFT_DAY', ...}
        Effect: Caller stops simulation on April 23, user manually
                advances to April 24 and triggers draft dialog.

    Args:
        next_date: ISO-formatted date string for TOMORROW

    Returns:
        Milestone dict if next_date has interactive event, None otherwise

    See Also:
        docs/architecture/milestone_detection_pattern.md for full explanation
    """
    # Query events for NEXT date (tomorrow)
    events = self._event_db.get_events_by_dynasty_and_timestamp(
        dynasty_id=self.dynasty_id,
        target_date=next_date  # Tomorrow's date
    )

    # Check for interactive event types
    for event in events:
        if event['type'] in ['DRAFT_DAY', 'TRADE_DEADLINE', 'FA_WINDOW_OPEN']:
            logger.debug(
                f"Interactive milestone found on {next_date} "
                f"(current date: {self._current_date}). "
                "Signaling stop before milestone."
            )
            return {
                'type': event['type'],
                'date': next_date,
                'requires_stop': True
            }

    return None
```

**File**: `ui/controllers/simulation_controller.py`

```python
def check_for_draft_day_event(self) -> bool:
    """
    Check if Draft Day is TOMORROW (look-ahead pattern).

    This checks tomorrow's date because we want to stop BEFORE draft day,
    not ON draft day. This gives user control over draft experience.

    Returns:
        True if tomorrow is draft day, False otherwise
    """
    tomorrow_date = self._calculate_next_date()

    events = self._event_db.get_events_by_dynasty_and_timestamp(
        dynasty_id=self.dynasty_id,
        target_date=tomorrow_date  # Check tomorrow
    )

    return any(e['type'] == 'DRAFT_DAY' for e in events)
```

#### Phase 2: Architecture Documentation (0.5 hours)

**File**: `docs/architecture/milestone_detection_pattern.md` (NEW)

Create comprehensive document (see content above in Option D section).

#### Phase 3: Unit Test Documentation (0.5 hours)

**File**: `tests/season/test_milestone_lookahead_pattern.py` (NEW)

```python
"""
Test suite documenting the look-ahead milestone detection pattern.

These tests serve as executable documentation for why we check TOMORROW
instead of TODAY for milestones.
"""

def test_lookahead_stops_before_milestone():
    """
    PATTERN DEMO: Simulation stops BEFORE milestone day.

    Setup:
        - Current date: April 23
        - Draft Day: April 24
        - Week simulation: April 23-29

    Expected:
        - Simulate April 23
        - Check April 24 (tomorrow)
        - Find Draft Day
        - STOP (don't simulate April 24)
        - User controls April 24
    """
    controller = SeasonCycleController(...)

    # Set current date to April 23
    controller._set_date("2025-04-23")

    # Create Draft Day on April 24 (tomorrow)
    event_db.create_event(
        dynasty_id=dynasty_id,
        event_type="DRAFT_DAY",
        event_date="2025-04-24"
    )

    # Simulate week
    result = controller.advance_week()

    # Verify stopped BEFORE April 24
    assert result['stopped_before_milestone'] is True
    assert result['milestone_date'] == "2025-04-24"
    assert controller.current_date == "2025-04-23"  # Still on April 23

    # User can now control April 24
    controller.advance_day()  # User manually advances
    assert controller.current_date == "2025-04-24"  # Now on Draft Day

def test_same_day_check_would_miss_milestone():
    """
    ANTI-PATTERN DEMO: Shows why checking TODAY doesn't work.

    If we checked TODAY instead of TOMORROW, we'd auto-simulate
    the milestone day before user could interact.
    """
    controller = SeasonCycleController(...)

    # Set current date to April 24 (Draft Day)
    controller._set_date("2025-04-24")

    # Create Draft Day on April 24 (TODAY)
    event_db.create_event(
        dynasty_id=dynasty_id,
        event_type="DRAFT_DAY",
        event_date="2025-04-24"
    )

    # If we simulate first, then check...
    controller.advance_day()  # Simulates April 24

    # Check for milestone on current date (April 24)
    milestone = controller.check_milestone_on_current_date()

    # TOO LATE! April 24 already simulated
    assert controller.current_date == "2025-04-25"  # Already advanced
    assert milestone is not None  # Found it, but too late

    # User can't control draft - it already happened
```

## Acceptance Criteria (Minimal Option D)

1. ✅ All milestone detection methods have comprehensive docstrings
2. ✅ Architecture doc explains look-ahead pattern with diagrams
3. ✅ Unit tests demonstrate pattern and anti-pattern
4. ✅ Variable names clarified (`next_date` vs `date`)
5. ✅ No functional changes to existing code
6. ✅ All existing tests still pass

## Timeline (Minimal Option D)

| Task | Time |
|------|------|
| Code documentation | 1h |
| Architecture doc | 0.5h |
| Unit tests | 0.5h |
| **Total** | **2h** |

## Future Considerations

**Revisit this issue if**:
1. We add 5+ interactive milestone types (event bus becomes worthwhile)
2. Multiple developers report confusion (more training needed)
3. We need milestone orchestration (e.g., "stop 2 days before draft")
4. Testing becomes difficult (better abstractions needed)

**Until then**: Pattern is correct, just needs documentation.

## References

- Current implementation: `src/season/season_cycle_controller.py:670-695`
- UI layer check: `ui/controllers/simulation_controller.py:521-545`
- Similar pattern: Database cursor look-ahead in iterator patterns
- Event detection: `src/events/event_database_api.py`