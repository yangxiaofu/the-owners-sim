# NFL Draft Event Integration Requirements

## Document Information
- **Version**: 1.0
- **Date**: 2025-11-23
- **Status**: Draft
- **Author**: Claude Code

## 1. Background

The NFL Draft is a critical offseason event where teams select new players to join their rosters. The simulation currently has all necessary infrastructure components:
- `DraftDayEvent` class in `src/events/draft_events.py`
- `DraftManager` in `src/offseason/draft_manager.py`
- `DraftDayDialog` UI in `ui/dialogs/draft_day_dialog.py`

However, the draft event is not currently scheduled in the offseason calendar, preventing it from being executed as part of the normal season cycle. This document outlines requirements for integrating the draft into the offseason calendar system.

## 2. User Requirements

### UR-1: Interactive Draft Requirement
**Priority**: CRITICAL
**Description**: The NFL Draft must always be interactive, requiring user engagement for all draft picks.
**Rationale**: The draft is a cornerstone experience in dynasty simulation games. User decision-making during the draft is essential for building team identity and player engagement.
**Acceptance Criteria**:
- Draft cannot be auto-simulated or skipped
- User must manually select or confirm each pick for their team
- AI teams auto-pick but user must advance through each pick

### UR-2: Non-Modal Dialog Requirement
**Priority**: HIGH
**Description**: The draft dialog must be non-modal, allowing users to switch between application tabs during the draft.
**Rationale**: Users need to reference team rosters, depth charts, salary cap status, and player statistics while making draft decisions.
**Acceptance Criteria**:
- Draft dialog does not block access to main window tabs
- User can navigate to Team, Player, and League tabs during draft
- Draft state persists when dialog loses focus

### UR-3: Save and Resume Support
**Priority**: HIGH
**Description**: The system must support saving draft progress and resuming a partial draft later.
**Rationale**: The NFL Draft consists of 262 picks over 7 rounds, which may take significant time. Users need the ability to take breaks and resume later.
**Acceptance Criteria**:
- Draft progress saved to database after each pick
- User can close dialog mid-draft without losing progress
- Reopening dialog resumes from last completed pick
- Draft state persists across application restarts

### UR-4: Scheduled Draft Date
**Priority**: HIGH
**Description**: The draft must be scheduled for April 24 each year in the offseason calendar.
**Rationale**: Reflects realistic NFL offseason timeline (post-Super Bowl, post-free agency).
**Acceptance Criteria**:
- Draft event created on April 24 during offseason initialization
- Date advances each season year (e.g., 2025-04-24, 2026-04-24)
- Event scheduled after Super Bowl and free agency period

## 3. Functional Requirements

### FR-1: Calendar Event Scheduling
**Priority**: CRITICAL
**Description**: DraftDayEvent must be scheduled in the offseason event calendar.
**Implementation Location**: `src/offseason/offseason_controller.py` or offseason event initialization
**Acceptance Criteria**:
- `DraftDayEvent` created with `event_date = April 24, {current_season_year}`
- Event stored in events database with correct dynasty_id
- Event appears in calendar view UI

### FR-2: Simulation Pause and Dialog Display
**Priority**: CRITICAL
**Description**: When simulation reaches April 24, it must pause and display the draft dialog.
**Implementation Location**: `src/calendar/simulation_executor.py` and `ui/controllers/simulation_controller.py`
**Acceptance Criteria**:
- `SimulationExecutor` detects DraftDayEvent execution
- Simulation pauses automatically (does not advance past April 24)
- `DraftDayDialog` opened automatically via `SimulationController`
- Dialog displayed with "Pick 1 of 262" initial state

### FR-3: Interactive Draft Pick Selection
**Priority**: CRITICAL
**Description**: User must be able to make draft picks via interactive UI.
**Implementation Location**: `ui/dialogs/draft_day_dialog.py`
**Acceptance Criteria**:
- Dialog displays current pick information (round, pick number, team)
- User can browse available players and view player details
- "Make Pick" button executes selection via `DraftManager`
- AI teams auto-pick when their turn arrives
- Dialog advances to next pick after selection

### FR-4: Draft Progress Persistence
**Priority**: HIGH
**Description**: Draft progress must be saved to database after each pick.
**Implementation Location**: `src/database/dynasty_state_api.py` or new draft state tracking
**Acceptance Criteria**:
- Current pick number stored in database
- Draft status tracked (in_progress, completed)
- Database updated after each successful pick
- Progress queryable for resume functionality

### FR-5: Mid-Draft Resume Capability
**Priority**: HIGH
**Description**: User can close dialog mid-draft and resume later without losing progress.
**Implementation Location**: `ui/dialogs/draft_day_dialog.py` and `ui/controllers/simulation_controller.py`
**Acceptance Criteria**:
- "Close" button available in dialog (does not mark draft complete)
- Closing dialog saves current state and returns to main window
- Re-triggering DraftDayEvent reopens dialog at current pick
- Dialog displays "Pick X of 262" showing progress

### FR-6: Simulation Control Lockout
**Priority**: MEDIUM
**Description**: Simulation controls must be disabled while draft is in progress.
**Implementation Location**: `ui/controllers/simulation_controller.py`
**Acceptance Criteria**:
- "Advance Day" button disabled when draft in progress
- "Advance Week" button disabled when draft in progress
- Status message indicates "Draft in progress - complete to continue"
- Controls re-enabled after draft completion

### FR-7: Draft Completion Handling
**Priority**: HIGH
**Description**: Completing all 262 picks must mark the event as executed and allow simulation to continue.
**Implementation Location**: `ui/dialogs/draft_day_dialog.py` and `src/events/draft_events.py`
**Acceptance Criteria**:
- Final pick (262) triggers draft completion
- DraftDayEvent marked as executed in database
- Dialog displays completion message and closes
- Simulation controls re-enabled
- Calendar advances past April 24

### FR-8: Draft Status Display
**Priority**: MEDIUM
**Description**: Dialog must clearly display draft progress and current status.
**Implementation Location**: `ui/dialogs/draft_day_dialog.py`
**Acceptance Criteria**:
- Header shows "Pick X of 262" (e.g., "Pick 15 of 262")
- Round and pick number displayed (e.g., "Round 1, Pick 15")
- Current team on the clock displayed
- Time remaining (if clock enabled) displayed

## 4. Non-Functional Requirements

### NFR-1: UI Responsiveness
**Priority**: HIGH
**Description**: Draft dialog must remain responsive without UI freezing during operations.
**Acceptance Criteria**:
- Pick execution completes within 100ms
- AI picks execute without blocking UI thread
- Dialog animation and scrolling remain smooth
- No "Application Not Responding" errors

### NFR-2: State Persistence Reliability
**Priority**: CRITICAL
**Description**: Draft state must reliably persist across application restarts.
**Acceptance Criteria**:
- Draft progress survives application crash
- Database writes confirmed before dialog advances
- No data loss during abnormal shutdown
- State recovery validated on application restart

### NFR-3: Architectural Consistency
**Priority**: HIGH
**Description**: Integration must follow existing architecture patterns.
**Acceptance Criteria**:
- Uses existing `EventDatabaseAPI` for event storage
- Uses existing `DynastyStateAPI` for state persistence
- Follows MVC pattern (View → Controller → Domain Model → API)
- Integrates with existing `SimulationExecutor` event handling

### NFR-4: Backward Compatibility
**Priority**: HIGH
**Description**: Integration must not break existing draft functionality.
**Acceptance Criteria**:
- Existing `DraftManager` API unchanged
- Demo scripts continue to work (if any)
- Manual draft triggering still supported (for testing)
- No breaking changes to public APIs

## 5. Design Decisions

### DD-1: Always Interactive Design
**Decision**: Draft will always require user interaction, with no auto-simulate option.
**Rationale**:
- Draft is a core engagement mechanic in dynasty simulation
- Auto-simulation would diminish strategic depth
- User investment in draft picks builds team identity
**Implications**:
- Simulation must always pause on April 24
- No "quick simulate" bypass option
- AI draft logic only for CPU teams

### DD-2: Non-Modal Dialog Pattern
**Decision**: Draft dialog will be non-modal, allowing tab navigation.
**Rationale**:
- Users need access to team data during draft (rosters, depth charts, cap space)
- Player scouting requires viewing player statistics and projections
- Flexibility improves user experience
**Implications**:
- Dialog managed as independent window, not modal QDialog
- Draft state must handle focus loss gracefully
- Main window tabs remain accessible

### DD-3: Save Progress Architecture
**Decision**: Draft progress saved after each pick, not just on dialog close.
**Rationale**:
- Long event (262 picks) increases crash risk
- Immediate persistence prevents data loss
- Supports application restart mid-draft
**Implications**:
- Database write after every pick (performance consideration)
- State recovery logic on dialog open
- Pick validation before database commit

### DD-4: UI Code Location
**Decision**: Move draft dialog from `demo/` to `ui/dialogs/` (production code).
**Rationale**:
- Draft is core simulation feature, not demo/test code
- Production location indicates supported feature
- Consistent with other UI dialog locations
**Implications**:
- Import path changes (update references)
- Production-level error handling required
- Comprehensive testing needed

## 6. Out of Scope

The following items are explicitly **out of scope** for this integration:

### OS-1: Auto-Draft AI Configuration
**Description**: Settings to configure AI auto-draft behavior or user preference for auto-draft.
**Rationale**: Draft is always interactive by design (UR-1).
**Future Consideration**: May revisit if user feedback demands quick-simulate option.

### OS-2: Draft Trade Functionality
**Description**: Trading draft picks during the draft.
**Rationale**: Trade logic already exists in `DraftManager` (out of scope for calendar integration).
**Future Consideration**: Trade UI may be added to dialog in future iteration.

### OS-3: Multi-User Draft
**Description**: Support for multiplayer draft sessions (multiple human users).
**Rationale**: Current architecture supports single-dynasty, single-user simulation.
**Future Consideration**: Major feature requiring networking/concurrency architecture.

### OS-4: Draft Clock Timer
**Description**: Real-time countdown timer for pick selection (e.g., 10 minutes per pick).
**Rationale**: Not essential for initial integration; adds complexity.
**Future Consideration**: Optional feature for enhanced realism.

### OS-5: Draft Lottery System
**Description**: NBA-style lottery for draft order determination.
**Rationale**: NFL uses fixed draft order based on standings (already implemented).
**Future Consideration**: N/A for NFL simulation.

## 7. Dependencies

### Internal Dependencies
- **Calendar System**: `src/calendar/calendar_manager.py`, `src/calendar/event_manager.py`
- **Event System**: `src/events/draft_events.py`, `src/events/event_database_api.py`
- **Draft Manager**: `src/offseason/draft_manager.py`
- **Dynasty State**: `src/database/dynasty_state_api.py`
- **Simulation Executor**: `src/calendar/simulation_executor.py`
- **UI Controllers**: `ui/controllers/simulation_controller.py`

### External Dependencies
- **PySide6**: Qt framework for non-modal dialog support
- **SQLite**: Database persistence for draft state

## 8. Acceptance Testing Scenarios

### AT-1: First Draft Execution
**Given**: New dynasty, simulation advanced to April 24, 2025
**When**: User clicks "Advance Day" on April 23, 2025
**Then**:
- Simulation pauses on April 24, 2025
- Draft dialog opens showing "Pick 1 of 262"
- "Advance Day" button disabled

### AT-2: Mid-Draft Close and Resume
**Given**: Draft dialog open at Pick 50 of 262
**When**: User closes dialog and reopens draft event
**Then**:
- Dialog reopens showing "Pick 50 of 262"
- All previous picks persisted in database
- User can continue from Pick 50

### AT-3: Draft Completion
**Given**: Draft dialog at Pick 262 of 262
**When**: User makes final pick (Mr. Irrelevant)
**Then**:
- Completion message displayed
- Dialog closes automatically
- DraftDayEvent marked executed in database
- Simulation controls re-enabled
- Calendar advances past April 24

### AT-4: Tab Navigation During Draft
**Given**: Draft dialog open at Pick 100 of 262
**When**: User clicks "Team" tab in main window
**Then**:
- Team tab displays roster and depth chart
- Draft dialog remains open (non-modal)
- User can return to draft dialog to continue

### AT-5: Application Restart Mid-Draft
**Given**: Draft in progress at Pick 75 of 262
**When**: User closes application and restarts
**Then**:
- Dynasty loads with draft state preserved
- Calendar shows April 24 with draft in progress
- Re-triggering draft opens dialog at Pick 75

## 9. Success Metrics

### SM-1: Integration Success
- Draft event scheduled on April 24 in 100% of new dynasties
- Draft dialog triggers on simulation advance to April 24
- Zero crashes during draft execution

### SM-2: User Experience
- Users can complete full 262-pick draft without data loss
- Draft progress saves after each pick (100% reliability)
- Non-modal dialog allows tab navigation during draft

### SM-3: Performance
- Pick execution completes within 100ms (95th percentile)
- Database writes do not block UI thread
- Dialog remains responsive during AI picks

### SM-4: Reliability
- Draft state survives application restart (100% recovery rate)
- No draft progress lost due to crashes or errors
- All 262 picks correctly persisted to database

## 10. Risk Assessment

### Risk-1: Long-Running Transaction Performance
**Description**: Saving after each pick (262 database writes) may impact performance.
**Likelihood**: Medium
**Impact**: Low
**Mitigation**: Use transaction batching (e.g., commit every 10 picks) with rollback safety.

### Risk-2: Dialog State Corruption
**Description**: Focus loss or UI events may corrupt draft state.
**Likelihood**: Low
**Impact**: High
**Mitigation**: Comprehensive state validation on dialog open, defensive state guards.

### Risk-3: Calendar Drift Recurrence
**Description**: Draft event execution may trigger calendar drift bug (silent persistence failure).
**Likelihood**: Medium
**Impact**: Critical
**Mitigation**: Add explicit state verification after draft completion, fail-loud on persistence errors.

### Risk-4: Backward Compatibility Breakage
**Description**: Integration may break existing draft or offseason functionality.
**Likelihood**: Low
**Impact**: High
**Mitigation**: Comprehensive regression testing, feature flag for gradual rollout.

## 11. Implementation Priority

### Phase 1: Core Integration (CRITICAL)
- FR-1: Calendar event scheduling
- FR-2: Simulation pause and dialog display
- FR-3: Interactive draft pick selection
- FR-7: Draft completion handling

### Phase 2: Persistence (HIGH)
- FR-4: Draft progress persistence
- FR-5: Mid-draft resume capability
- NFR-2: State persistence reliability

### Phase 3: Polish (MEDIUM)
- FR-6: Simulation control lockout
- FR-8: Draft status display
- NFR-1: UI responsiveness

### Phase 4: Validation (HIGH)
- NFR-3: Architectural consistency
- NFR-4: Backward compatibility
- Acceptance testing scenarios

## 12. Open Questions

### OQ-1: Draft State Storage Location
**Question**: Should draft state be stored in `dynasty_state` table or new `draft_state` table?
**Options**:
- A) Add `draft_pick_number` column to `dynasty_state` (simple, denormalized)
- B) Create new `draft_state` table (normalized, more flexible)
**Recommendation**: Option A for Phase 1 (simpler), Option B for future multi-draft support.

### OQ-2: AI Pick Timing
**Question**: Should AI picks execute immediately or with artificial delay?
**Options**:
- A) Immediate execution (fast, may feel unrealistic)
- B) 0.5-1 second delay per pick (slower, more realistic)
**Recommendation**: Option B with configurable delay for user preference.

### OQ-3: Draft Event Type
**Question**: Should draft be single event or 7 events (one per round)?
**Options**:
- A) Single `DraftDayEvent` for all 262 picks (current architecture)
- B) Seven `DraftRoundEvent` instances (more granular control)
**Recommendation**: Option A for simplicity, Option B for future multi-day draft support.

## 13. References

### Architecture Documents
- `docs/architecture/ui_layer_separation.md` - MVC pattern and domain model layer
- `docs/architecture/event_cap_integration.md` - Event system integration patterns
- `docs/plans/offseason_plan.md` - Offseason system architecture

### Related Code
- `src/events/draft_events.py` - DraftDayEvent implementation
- `src/offseason/draft_manager.py` - Draft execution logic
- `ui/dialogs/draft_day_dialog.py` - Draft UI dialog
- `src/calendar/simulation_executor.py` - Event execution framework

### Prior Art
- Franchise tag event integration (example of offseason calendar event)
- Free agency event scheduling (similar interactive offseason event)
