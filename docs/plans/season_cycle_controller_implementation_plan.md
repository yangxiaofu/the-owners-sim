# Season Cycle Controller - "Skip to New Season" Implementation Plan

**Status**: 🚧 IN PROGRESS - UI skeleton complete, backend logic pending
**Created**: 2025-10-19
**Last Updated**: 2025-10-19

## Overview

This document tracks the implementation of the "Skip to New Season" feature, which allows users to bypass all remaining offseason milestones and jump directly to the start of the next season (first Thursday in August - preseason start).

## Requirements

### User Story
As a user in the offseason, I want TWO buttons:
1. **"Sim to Next Milestone"** - Advances to next offseason event (franchise tags, draft, FA, etc.)
2. **"Skip to New Season"** - Bypasses ALL remaining offseason events and initializes the next season

### Technical Requirements
- **Preseason Start Date**: First Thursday in August (dynamically calculated, not fixed)
- **Auto-Execute Events**: All offseason events (franchise tags, draft, FA, roster cuts) must execute automatically
- **Button Visibility**: "Skip to New Season" button visible immediately when offseason starts
- **Season Initialization**: New 272-game schedule, reset standings, increment season year
- **Phase Transition**: Offseason → Regular Season

## Implementation Status

### ✅ Phase 1: Foundation (COMPLETE)

#### 1.1 Milestone Calculation System
**Files Modified**: `src/calendar/season_milestones.py`

- [x] Added `PRESEASON_START` to `MilestoneType` enum (line 43)
- [x] Added `_calculate_preseason_start()` method (lines 603-631)
  - Calculates first Thursday in August dynamically
  - Uses Python's `weekday()` to find correct date
  - Examples: 2024 = Aug 1, 2025 = Aug 7, 2026 = Aug 6
- [x] Added milestone definition in `_setup_standard_milestones()` (lines 304-313)

#### 1.2 Offseason Event Scheduling
**Files Modified**: `src/offseason/offseason_event_scheduler.py`

- [x] Added PRESEASON_START milestone event scheduling (lines 410-430)
- [x] Added `_calculate_first_thursday_august()` fallback helper (lines 432-455)
- [x] Event includes metadata: `{"calculation": "first_thursday_august"}`

#### 1.3 Backend Method Skeletons
**Files Modified**: `src/season/season_cycle_controller.py`

- [x] Added `simulate_to_new_season()` public method (lines 565-626)
  - Returns placeholder response with TODO message
  - Has proper error handling for wrong phase
  - Documents expected return format
- [x] Added helper method skeletons (lines 1261-1329):
  - `_get_remaining_offseason_events_until_preseason()` (lines 1263-1276)
  - `_execute_offseason_event_auto()` (lines 1278-1296)
  - `_initialize_next_season()` (lines 1298-1317)
  - `_reset_all_standings()` (lines 1319-1329)

#### 1.4 UI Layer Integration
**Files Modified**:
- `ui/controllers/simulation_controller.py` (lines 349-399)
- `ui/main_window.py` (lines 294-345, 601-628, 670-674)

- [x] Added `simulate_to_new_season()` wrapper in SimulationController
  - Calls backend method
  - Emits date_changed signal on success
  - Saves state to database
  - Proper error handling
- [x] Added "Skip to New Season" button to main window
  - Created action in `_create_toolbar()`
  - Added visibility logic in `_on_date_changed()`
  - Added click handler `_on_skip_to_new_season()`
  - Confirmation dialog before execution
  - Success/error message popups

### 🚧 Phase 2: Backend Implementation (TODO)

#### 2.1 Event Query Method
**File**: `src/season/season_cycle_controller.py`
**Method**: `_get_remaining_offseason_events_until_preseason()`

**Implementation Steps**:
1. Get current calendar date
2. Query `EventDatabaseAPI` for all events after current date:
   - Event types: `['DEADLINE', 'WINDOW', 'MILESTONE']`
   - Dynasty ID and season year filters
3. Filter events until PRESEASON_START (inclusive)
4. Return sorted list of event dicts

**Required Database API Method**:
```python
# May need to add to EventDatabaseAPI:
def get_events_by_type_and_date_range(
    self,
    dynasty_id: str,
    event_types: List[str],
    start_date: Date,
    season_year: int
) -> List[Dict[str, Any]]:
    """Get events filtered by type and date range."""
```

**Expected Return Format**:
```python
[
    {
        'event_id': str,
        'event_type': 'DEADLINE' | 'WINDOW' | 'MILESTONE',
        'event_date': Date,
        'display_name': str,
        'description': str,
        'deadline_type': str (if DEADLINE),
        'window_name': str (if WINDOW),
        'milestone_type': str (if MILESTONE),
        'metadata': Dict
    },
    # ... more events in chronological order
]
```

#### 2.2 Event Auto-Execution Method
**File**: `src/season/season_cycle_controller.py`
**Method**: `_execute_offseason_event_auto(event)`

**Implementation Phases**:

**Phase 2.2.1: Minimal Implementation** (For initial testing)
```python
def _execute_offseason_event_auto(self, event: Dict[str, Any]):
    """Auto-execute event - minimal placeholder for testing."""
    event_type = event.get('event_type')

    # Just log the event for now
    if self.verbose_logging:
        print(f"[AUTO-EXECUTE] {event.get('display_name')}")

    # Mark event as processed in database
    # (No actual game logic yet)
```

**Phase 2.2.2: Full Implementation** (Future enhancement)
```python
def _execute_offseason_event_auto(self, event: Dict[str, Any]):
    """Auto-execute offseason event with actual game logic."""
    event_type = event.get('event_type')

    if event_type == 'DEADLINE':
        deadline_type = event.get('deadline_type')

        if deadline_type == 'FRANCHISE_TAG':
            # TODO: Implement AI franchise tag logic
            # - Query top players by position
            # - Apply franchise tags to borderline FAs
            # - Use salary cap API to create tag contracts
            pass

        elif deadline_type == 'SALARY_CAP_COMPLIANCE':
            # TODO: Validate all 32 teams under cap
            # - Run cap compliance check
            # - Auto-restructure contracts if needed
            pass

        elif deadline_type == 'RFA_TENDER':
            # TODO: Implement RFA tender logic
            pass

        elif deadline_type == 'FINAL_ROSTER_CUTS':
            # TODO: Implement roster cut logic
            # - For each team, cut to 53-man roster
            # - Use player ratings to determine cuts
            pass

    elif event_type == 'MILESTONE':
        milestone_type = event.get('milestone_type')

        if milestone_type == 'DRAFT':
            # TODO: Auto-simulate draft
            # - Use DraftAPI to run 7-round draft
            # - AI teams make selections based on needs
            # - Generate draft class if not exists
            pass

        elif milestone_type == 'PRESEASON_START':
            # No action needed - just a marker event
            pass
```

**Dependencies for Full Implementation**:
- AI decision-making system for franchise tags
- AI draft selection logic
- AI free agency bidding algorithm
- Roster management AI (cuts, depth chart updates)

#### 2.3 Season Initialization Method
**File**: `src/season/season_cycle_controller.py`
**Method**: `_initialize_next_season()`

**Implementation Steps**:

**Step 1: Increment Season Year**
```python
old_year = self.season_year
self.season_year += 1

if self.verbose_logging:
    print(f"[NEW_SEASON] {old_year} → {self.season_year}")
```

**Step 2: Generate New Schedule**
```python
from ui.domain_models.season_data_model import SeasonDataModel

season_model = SeasonDataModel(
    db_path=self.database_path,
    dynasty_id=self.dynasty_id,
    season=self.season_year
)

# Regular season starts first Thursday after Labor Day (Sept 5 typical)
first_game_date = datetime(self.season_year, 9, 5)

success, error = season_model.generate_initial_schedule(first_game_date)

if not success:
    raise Exception(f"Failed to generate schedule: {error}")

if self.verbose_logging:
    print(f"[NEW_SEASON] Generated 272-game schedule")
```

**Step 3: Reset Standings**
```python
self._reset_all_standings()

if self.verbose_logging:
    print(f"[NEW_SEASON] Reset all 32 team standings to 0-0-0")
```

**Step 4: Update Dynasty State**
```python
# Update dynasty_state table with new season info
self.season_controller.dynasty_api.update_state(
    dynasty_id=self.dynasty_id,
    current_date=str(self.calendar.get_current_date()),
    current_week=1,
    current_phase='regular_season'
)

if self.verbose_logging:
    print(f"[NEW_SEASON] Updated dynasty_state")
```

**Step 5: Transition Phase**
```python
self.phase_state.phase = SeasonPhase.REGULAR_SEASON
self.active_controller = self.season_controller

if self.verbose_logging:
    print(f"[NEW_SEASON] Phase: OFFSEASON → REGULAR_SEASON")
```

**Step 6: Reinitialize Season Controller**
```python
# Update season controller's year
self.season_controller.season_year = self.season_year

# Reload schedule data
# (SeasonController should pick up new schedule from database)

if self.verbose_logging:
    print(f"[NEW_SEASON] Season {self.season_year} ready!")
```

**Error Handling**:
```python
try:
    # All steps above
    pass
except Exception as e:
    # Rollback season year
    self.season_year = old_year

    # Log error
    self.logger.error(f"Failed to initialize season {self.season_year + 1}: {e}")

    # Re-raise with context
    raise Exception(f"Season initialization failed: {e}") from e
```

#### 2.4 Standings Reset Method
**File**: `src/season/season_cycle_controller.py`
**Method**: `_reset_all_standings()`

**Implementation**:
```python
def _reset_all_standings(self):
    """Reset all 32 teams to 0-0-0 records for new season."""
    conn = self.database_api.db_connection.get_connection()
    cursor = conn.cursor()

    try:
        for team_id in range(1, 33):
            cursor.execute('''
                INSERT OR REPLACE INTO standings
                (dynasty_id, season, team_id, wins, losses, ties,
                 points_for, points_against, division_wins, division_losses,
                 conference_wins, conference_losses)
                VALUES (?, ?, ?, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            ''', (self.dynasty_id, self.season_year, team_id))

        conn.commit()

        if self.verbose_logging:
            print(f"[STANDINGS_RESET] All 32 teams reset to 0-0-0 for season {self.season_year}")

    except Exception as e:
        conn.rollback()
        raise Exception(f"Failed to reset standings: {e}") from e
```

**Alternative Using Database API**:
```python
# If DatabaseAPI has a bulk reset method:
self.database_api.reset_all_standings(
    dynasty_id=self.dynasty_id,
    season=self.season_year
)
```

#### 2.5 Main Skip Method Implementation
**File**: `src/season/season_cycle_controller.py`
**Method**: `simulate_to_new_season()`

**Full Implementation** (Replace placeholder at lines 565-626):
```python
def simulate_to_new_season(self, progress_callback=None) -> Dict[str, Any]:
    """Skip all remaining offseason milestones and initialize new season."""

    # Validation
    if self.phase_state.phase != SeasonPhase.OFFSEASON:
        return {
            'success': False,
            'message': 'Can only skip to new season during offseason',
            'starting_phase': self.phase_state.phase.value,
            'ending_phase': self.phase_state.phase.value,
            'weeks_simulated': 0,
            'total_games': 0,
            'phase_transition': False,
            'days_simulated': 0,
            'events_executed': 0
        }

    start_date = self.calendar.get_current_date()
    events_executed = []

    if self.verbose_logging:
        print(f"\n{'='*80}")
        print(f"{'SKIP TO NEW SEASON'.center(80)}")
        print(f"{'='*80}")

    # Get all remaining offseason events
    remaining_events = self._get_remaining_offseason_events_until_preseason()
    total_events = len(remaining_events)

    if self.verbose_logging:
        print(f"[SKIP] Found {total_events} events to auto-execute")

    # Execute each event in chronological order
    for idx, event in enumerate(remaining_events):
        event_date = event['event_date']
        event_name = event.get('display_name', 'Unknown Event')

        # Advance calendar to event date
        while self.calendar.get_current_date() < event_date:
            self.calendar.advance(1)

        # Execute event (franchise tags, draft, etc.)
        try:
            self._execute_offseason_event_auto(event)
            events_executed.append(event_name)

            if self.verbose_logging:
                print(f"  [{idx+1}/{total_events}] {event_name} - {event_date}")

        except Exception as e:
            self.logger.error(f"Error executing event {event_name}: {e}")
            # Continue with other events (non-fatal)

        # Progress callback for UI
        if progress_callback:
            progress_callback(idx + 1, total_events, event_name)

    # Initialize new season
    try:
        self._initialize_next_season()
    except Exception as e:
        # Fatal error - return failure
        return {
            'success': False,
            'message': f'Season initialization failed: {str(e)}',
            'starting_phase': 'offseason',
            'ending_phase': 'offseason',
            'weeks_simulated': 0,
            'total_games': 0,
            'phase_transition': False,
            'days_simulated': 0,
            'events_executed': len(events_executed),
            'event_list': events_executed
        }

    # Success!
    end_date = self.calendar.get_current_date()
    days_simulated = start_date.days_until(end_date)

    if self.verbose_logging:
        print(f"\n[SKIP] Season {self.season_year} initialized successfully!")
        print(f"  Events executed: {len(events_executed)}")
        print(f"  Days simulated: {days_simulated}")
        print(f"  Start date: {start_date}")
        print(f"  End date: {end_date}")
        print(f"{'='*80}\n")

    return {
        'success': True,
        'start_date': str(start_date),
        'end_date': str(end_date),
        'starting_phase': 'offseason',
        'ending_phase': 'regular_season',
        'weeks_simulated': days_simulated // 7,
        'total_games': 0,
        'phase_transition': True,
        'days_simulated': days_simulated,
        'events_executed': len(events_executed),
        'event_list': events_executed,
        'new_season_year': self.season_year,
        'message': f'Season {self.season_year} initialized! {len(events_executed)} offseason events auto-executed.'
    }
```

## Testing Plan

### Phase 1 Testing (UI Flow - Can Test Now)
1. ✅ Run application and complete season to Super Bowl
2. ✅ Verify both buttons appear in offseason ("Sim to Next Milestone" + "Skip to New Season")
3. ✅ Click "Skip to New Season"
4. ✅ Verify confirmation dialog appears
5. ✅ Click "Yes" - should see placeholder error message
6. ✅ Verify button disappears when not in offseason

### Phase 2 Testing (Backend Implementation - After TODO completion)
1. ⏳ Click "Skip to New Season" in February
2. ⏳ Verify all offseason events execute (check logs)
3. ⏳ Verify calendar advances to first Thursday in August
4. ⏳ Verify new season schedule exists (272 games)
5. ⏳ Verify standings reset to 0-0-0
6. ⏳ Verify season year incremented
7. ⏳ Verify phase changed to REGULAR_SEASON
8. ⏳ Simulate first game of new season to confirm working

## Implementation Priority

### Immediate (Can Test UI Flow)
- ✅ All Phase 1 work complete
- ✅ UI buttons functional (show placeholder message)

### Short-term (Minimal Backend for Basic Testing)
1. Implement `_get_remaining_offseason_events_until_preseason()` (simple database query)
2. Implement minimal `_execute_offseason_event_auto()` (just logging, no game logic)
3. Implement `_reset_all_standings()` (simple database update)
4. Implement `_initialize_next_season()` (schedule generation + phase transition)
5. Update `simulate_to_new_season()` to call helpers
6. Test end-to-end flow (skip should work, but no AI event execution)

### Long-term (Full Feature)
1. Implement AI franchise tag logic
2. Implement AI draft simulation
3. Implement AI free agency logic
4. Implement AI roster cuts logic
5. Add comprehensive error recovery
6. Add detailed progress tracking for UI

## Files to Implement

### High Priority (For Basic Functionality)
- [ ] `src/season/season_cycle_controller.py` - Complete all 4 helper methods
- [ ] `src/events/event_database_api.py` - Add `get_events_by_type_and_date_range()` if needed

### Medium Priority (For Full Feature)
- [ ] Create AI decision-making modules for each offseason event type
- [ ] Integrate with existing DraftAPI for draft simulation
- [ ] Integrate with salary cap system for contract operations

### Low Priority (Polish)
- [ ] Add detailed progress UI with event-by-event updates
- [ ] Add "Cancel" capability during skip operation
- [ ] Add preview of what will happen before execution

## Known Limitations

1. **No AI Logic Yet**: Events are marked as executed but don't affect game state (placeholder)
2. **No Rollback**: If season initialization fails, may leave database in inconsistent state
3. **No Progress Details**: UI shows generic progress, not event-by-event updates
4. **No Preview**: User can't see what will happen before clicking "Yes"

## Future Enhancements

1. **Smart Skip Options**: Allow user to stop at specific milestones (e.g., "Skip to Draft")
2. **Event Review**: Show summary of what happened during skip (players drafted, FAs signed, etc.)
3. **Configurable AI**: Let user control how aggressive AI is with cap management, trades, etc.
4. **Undo Capability**: Allow reverting to before skip (requires save state)

## Related Documentation

- `docs/plans/offseason_plan.md` - Offseason event system architecture
- `docs/architecture/event_cap_integration.md` - Event-salary cap bridge pattern
- `docs/plans/full_season_simulation_plan.md` - Complete season cycle design
- `src/calendar/season_milestones.py` - Milestone calculation system
- `src/offseason/offseason_event_scheduler.py` - Event scheduling logic

## Change Log

**2025-10-19**: Initial creation
- Documented all Phase 1 work (complete)
- Created detailed implementation plan for Phase 2
- Added testing plan and priority matrix
