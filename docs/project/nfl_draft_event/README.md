# NFL Draft Event Scheduling Integration

**Add NFL Draft Day event scheduling to offseason calendar with interactive UI dialog integration**

## Project Overview

This project integrates the NFL Draft Day event into the offseason calendar system and ensures proper UI interaction when draft day arrives. Currently, the draft event is not scheduled in the offseason calendar, resulting in no event being triggered on April 24 (draft day) and no user interaction occurring.

## Problem Statement

The NFL Draft is a critical offseason event, but it is currently missing from the automated event scheduling system:

- **Missing Event Scheduling**: No `DraftDayEvent` is created when the offseason calendar is initialized
- **No Event Detection**: `SimulationController` does not detect when draft day arrives during simulation
- **No UI Interaction**: The `DraftDayDialog` is never triggered, preventing user participation in the draft
- **Silent Skip**: The simulation continues past draft day without any draft activity or user notification

This creates a significant gap in the offseason simulation flow, as teams cannot select draft picks and rosters remain incomplete entering the new season.

## Solution Approach

The solution involves three key integration points:

1. **Calendar Integration** (`src/offseason/offseason_controller.py`)
   - Schedule `DraftDayEvent` on April 24 during offseason initialization
   - Ensure event is created for all dynasties with proper metadata

2. **Event Detection** (`ui/controllers/simulation_controller.py`)
   - Detect `DraftDayEvent` in `_check_for_special_events()` method
   - Add case for draft event type alongside existing free agency detection

3. **UI Triggering** (`ui/controllers/simulation_controller.py`)
   - Launch `DraftDayDialog` when draft event is detected
   - Use non-modal dialog to allow UI access during draft
   - Support save/resume for partial drafts

## Key Features

- **Always Interactive**: Draft dialog always appears on draft day (no AI-only mode)
- **Non-Modal Dialog**: Users can access other UI features during the draft (roster, depth chart, etc.)
- **Save/Resume Capability**: Support for pausing and resuming partial drafts
- **Component Reuse**: Leverages existing `DraftDayEvent`, `DraftManager`, and `DraftDayDialog` components
- **Calendar Integration**: Draft event appears in calendar UI with proper scheduling
- **Dynasty Isolation**: Works correctly with multiple dynasty saves

## Current Status

**Phase**: Planning and Documentation

**Progress**:
- ✅ Problem analysis complete
- ✅ Solution approach defined
- ✅ Documentation structure created
- ⏳ Implementation plan in progress
- ⏳ Architecture documentation in progress
- ⏳ API specifications pending

**Next Steps**:
1. Complete implementation plan document
2. Document architecture and integration points
3. Create API specification for event scheduling
4. Begin implementation of calendar integration
5. Implement event detection in SimulationController
6. Add UI triggering logic for draft dialog

## Documentation Index

- **[Implementation Plan](./implementation_plan.md)** - Detailed implementation phases and tasks *(pending)*
- **[Architecture](./architecture.md)** - System architecture and integration points *(pending)*
- **[API Specification](./api_specification.md)** - Event scheduling and detection API *(pending)*
- **[Testing Strategy](./testing_strategy.md)** - Test plan and validation approach *(pending)*

## Quick Links

### Source Code Files

**Event System**:
- `/Users/fudong/Library/CloudStorage/OneDrive-Personal/1.Projects/the-owners-sim/src/events/draft_events.py` - DraftDayEvent definition
- `/Users/fudong/Library/CloudStorage/OneDrive-Personal/1.Projects/the-owners-sim/src/events/event_database_api.py` - Event storage and retrieval

**Offseason System**:
- `/Users/fudong/Library/CloudStorage/OneDrive-Personal/1.Projects/the-owners-sim/src/offseason/offseason_controller.py` - Offseason calendar initialization
- `/Users/fudong/Library/CloudStorage/OneDrive-Personal/1.Projects/the-owners-sim/src/offseason/draft_manager.py` - Draft execution logic

**UI System**:
- `/Users/fudong/Library/CloudStorage/OneDrive-Personal/1.Projects/the-owners-sim/ui/controllers/simulation_controller.py` - Event detection and UI triggering
- `/Users/fudong/Library/CloudStorage/OneDrive-Personal/1.Projects/the-owners-sim/ui/dialogs/draft_day_dialog.py` - Draft day interactive dialog

**Calendar System**:
- `/Users/fudong/Library/CloudStorage/OneDrive-Personal/1.Projects/the-owners-sim/src/calendar/calendar_manager.py` - Calendar management
- `/Users/fudong/Library/CloudStorage/OneDrive-Personal/1.Projects/the-owners-sim/src/calendar/simulation_executor.py` - Event execution orchestration

### Related Documentation

- **[Offseason Plan](../../plans/offseason_plan.md)** - Overall offseason system architecture
- **[UI Development Plan](../../plans/ui_development_plan.md)** - Desktop UI development roadmap
- **[Event System Documentation](../../architecture/event_cap_integration.md)** - Event system architecture

## Contributing

When working on this project:

1. **Follow Existing Patterns**: Use the `FranchiseTagEvent` and `DraftDayDialog` patterns as reference implementations
2. **Maintain Dynasty Isolation**: Ensure all changes respect dynasty context
3. **Test Thoroughly**: Verify calendar scheduling, event detection, and UI interaction
4. **Document Changes**: Update relevant documentation files as implementation progresses

## Project Goals

**Primary Goal**: Enable seamless draft day experience where users can participate in the NFL Draft during offseason simulation

**Success Criteria**:
- Draft event appears on April 24 in calendar UI
- Simulation pauses automatically when draft day arrives
- Draft dialog opens and allows user to make picks
- Draft can be saved and resumed across multiple sessions
- All picks are properly recorded and integrated with roster system
- System works correctly for all dynasties and database configurations

---

**Last Updated**: 2025-11-23
**Project Lead**: Claude Code
**Status**: Planning Phase
