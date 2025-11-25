# Simulation Execution Flow Diagrams

**Purpose:** Visual reference for simulation advancement flows
**Audience:** All developers
**Related:** [Main Audit Report](simulation_execution_flow_audit.md) | [Issues Tracker](issues_tracker.md)

---

## Table of Contents

1. [Day Advancement Flow](#day-advancement-flow)
2. [Week Advancement Flow](#week-advancement-flow)
3. [Milestone Simulation Flow](#milestone-simulation-flow)
4. [Phase Transition Flow](#phase-transition-flow)
5. [State Persistence Flow](#state-persistence-flow)
6. [Component Interaction Diagram](#component-interaction-diagram)
7. [Call Stack Traces](#call-stack-traces)

---

## Day Advancement Flow

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                       USER ACTION                           │
│              [Click "Advance Day" Button]                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     UI VIEW LAYER                           │
│         ui/views/season_view.py                             │
│         └─ _on_simulate_day()                               │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  UI CONTROLLER LAYER                        │
│         ui/controllers/simulation_controller.py             │
│         └─ advance_day()                                    │
│            └─ _execute_simulation_with_persistence()        │
│               ├─ Call backend (season_controller)          │
│               ├─ Extract state (via hook)                   │
│               ├─ Pre-save hook (phase transition check)     │
│               ├─ _save_state_to_db() ✅ FAIL-LOUD           │
│               ├─ Post-save hook (emit signals)              │
│               └─ Exception handling (retry/reload/abort)    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              SIMULATION ORCHESTRATION LAYER                 │
│         src/season/season_cycle_controller.py               │
│         └─ advance_day()                                    │
│            ├─ Auto-recover guard                            │
│            ├─ calendar.advance(days=1) ← OWNS CALENDAR      │
│            ├─ Check phase transition (BEFORE handler)       │
│            ├─ Get phase handler                             │
│            ├─ handler.simulate_day(current_date)            │
│            ├─ Update statistics                             │
│            ├─ Check transactions                            │
│            ├─ Check phase transition (AFTER handler)        │
│            └─ Return result dict                            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    PHASE HANDLER LAYER                      │
│         OffseasonHandler / RegularSeasonHandler / etc.      │
│         └─ simulate_day(current_date)                       │
│            ├─ Read current_date (READ-ONLY)                 │
│            ├─ Execute phase-specific logic                  │
│            ├─ Call simulation_executor                      │
│            └─ Return events/games                           │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   EVENT EXECUTION LAYER                     │
│         src/calendar/simulation_executor.py                 │
│         └─ simulate_day(current_date)                       │
│            ├─ Query events for current_date                 │
│            ├─ Execute each event                            │
│            └─ Return events_executed                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     DATABASE LAYER                          │
│         data/database/nfl_simulation.db                     │
│         └─ State persisted (current_date, current_phase)    │
└─────────────────────────────────────────────────────────────┘
```

### Detailed Sequence Diagram

```
User              UI View         UI Controller      Season Controller   Phase Handler   Executor      Database
 │                   │                 │                    │                  │             │             │
 │ Click "Day"       │                 │                    │                  │             │             │
 ├──────────────────>│                 │                    │                  │             │             │
 │                   │ advance_day()   │                    │                  │             │             │
 │                   ├────────────────>│                    │                  │             │             │
 │                   │                 │ advance_day()      │                  │             │             │
 │                   │                 ├───────────────────>│                  │             │             │
 │                   │                 │                    │ auto_recover()   │             │             │
 │                   │                 │                    ├─────────────────────────────────────────────>│
 │                   │                 │                    │<─────────────────────────────────────────────┤
 │                   │                 │                    │                  │             │             │
 │                   │                 │                    │ calendar.advance(1)            │             │
 │                   │                 │                    ├──────────────────┤             │             │
 │                   │                 │                    │ ✅ Calendar: +1   │             │             │
 │                   │                 │                    │                  │             │             │
 │                   │                 │                    │ check_phase_transition()       │             │
 │                   │                 │                    ├──────────────────┤             │             │
 │                   │                 │                    │                  │             │             │
 │                   │                 │                    │ handler.simulate_day(date)     │             │
 │                   │                 │                    ├─────────────────>│             │             │
 │                   │                 │                    │                  │ simulate_day(date)        │
 │                   │                 │                    │                  ├────────────>│             │
 │                   │                 │                    │                  │             │ query events│
 │                   │                 │                    │                  │             ├────────────>│
 │                   │                 │                    │                  │             │<────────────┤
 │                   │                 │                    │                  │             │ execute     │
 │                   │                 │                    │                  │<────────────┤             │
 │                   │                 │                    │<─────────────────┤             │             │
 │                   │                 │                    │                  │             │             │
 │                   │                 │                    │ update_statistics│             │             │
 │                   │                 │                    ├──────────────────┤             │             │
 │                   │                 │                    │                  │             │             │
 │                   │                 │                    │ check_phase_transition()       │             │
 │                   │                 │                    ├──────────────────┤             │             │
 │                   │                 │                    │                  │             │             │
 │                   │                 │<───────────────────┤                  │             │             │
 │                   │                 │ result: {success, date, phase, games}│             │             │
 │                   │                 │                    │                  │             │             │
 │                   │                 │ TEMPLATE METHOD PATTERN (ISSUE-002 Fix)             │             │
 │                   │                 │ _execute_simulation_with_persistence()              │             │
 │                   │                 │                    │                  │             │             │
 │                   │                 │ extract state      │                  │             │             │
 │                   │                 ├──────────────────┤ │                  │             │             │
 │                   │                 │                    │                  │             │             │
 │                   │                 │ pre-save hook      │                  │             │             │
 │                   │                 ├──────────────────┤ │                  │             │             │
 │                   │                 │ (phase transition) │                  │             │             │
 │                   │                 │                    │                  │             │             │
 │                   │                 │ save_state_to_db() │                  │             │             │
 │                   │                 ├─────────────────────────────────────────────────────────────────>│
 │                   │                 │ ✅ FAIL-LOUD       │                  │             │<────────────┤
 │                   │                 │                    │                  │             │             │
 │                   │                 │ update cache       │                  │             │             │
 │                   │                 ├──────────────────┤ │                  │             │             │
 │                   │                 │ (after save)       │                  │             │             │
 │                   │                 │                    │                  │             │             │
 │                   │                 │ post-save hook     │                  │             │             │
 │                   │                 ├──────────────────┤ │                  │             │             │
 │                   │                 │ emit signals       │                  │             │             │
 │                   │<────────────────┤                    │                  │             │             │
 │<──────────────────┤                 │                    │                  │             │             │
 │ UI Updated        │                 │                    │                  │             │             │
```

---

## Week Advancement Flow

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                       USER ACTION                           │
│              [Click "Advance Week" Button]                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  UI CONTROLLER LAYER                        │
│         ui/controllers/simulation_controller.py             │
│         └─ advance_week()                                   │
│            └─ _execute_simulation_with_persistence()        │
│               ├─ Call backend (season_controller)          │
│               ├─ Extract state (via hook)                   │
│               ├─ Pre-save hook (week tracking - DB query)   │
│               ├─ _save_state_to_db() ✅ FAIL-LOUD           │
│               ├─ Post-save hook (emit signals)              │
│               └─ Exception handling (retry/reload/abort)    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              SIMULATION ORCHESTRATION LAYER                 │
│         src/season/season_cycle_controller.py               │
│         └─ advance_week()                                   │
│            │                                                 │
│            │  ┌──────────────────────────────────┐          │
│            │  │  for day_num in range(7):        │          │
│            │  │    day_result = advance_day()    │          │
│            │  │    if phase_transition:          │          │
│            │  │      break  # Early exit         │          │
│            │  └──────────────────────────────────┘          │
│            │                                                 │
│            └─ Aggregate results from all days               │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼ (each day)
┌─────────────────────────────────────────────────────────────┐
│                  [Same as Day Flow Above]                   │
│         SeasonCycleController.advance_day()                 │
│         → Phase Handler → Executor → Database               │
└─────────────────────────────────────────────────────────────┘
```

### Loop Behavior

```
Week Start: 2025-03-01

Day 1:
  advance_day() → 2025-03-02
  ✅ Success, no transition

Day 2:
  advance_day() → 2025-03-03
  ✅ Success, no transition

Day 3:
  advance_day() → 2025-03-04
  ✅ Success, no transition

Day 4:
  advance_day() → 2025-03-05
  ✅ Success, no transition

Day 5:
  advance_day() → 2025-03-06
  ✅ Success, no transition

Day 6:
  advance_day() → 2025-03-07
  ✅ Success, no transition

Day 7:
  advance_day() → 2025-03-08
  ✅ Success, no transition

Week End: 2025-03-08
Days Advanced: 7
Total Games: 28 (4 per day × 7 days)
```

### Early Exit on Phase Transition

```
Week Start: 2025-02-01 (Offseason)

Day 1:
  advance_day() → 2025-02-02
  ✅ Success, no transition

Day 2:
  advance_day() → 2025-02-03
  ✅ Success, no transition

Day 3:
  advance_day() → 2025-02-04
  ⚠️  Phase Transition: Offseason → Preseason
  ❌ BREAK LOOP (don't continue to day 4)

Week End: 2025-02-04
Days Advanced: 3 (not 7)
Phase Changed: YES
```

---

## Milestone Simulation Flow

### Query and Simulate Flow

```
┌─────────────────────────────────────────────────────────────┐
│                       USER ACTION                           │
│          [Click "Simulate to Next Milestone"]               │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              SIMULATION ORCHESTRATION LAYER                 │
│         src/season/season_cycle_controller.py               │
│         └─ simulate_to_next_offseason_milestone()           │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     MILESTONE QUERY                         │
│         next_milestone = db.get_next_offseason_milestone()  │
│         Current Date: 2025-03-01                            │
│         Query Result: 2025-03-12 (Franchise Tag Deadline)   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  SIMULATE TO DATE LOOP                      │
│         simulate_to_date(target_date=2025-03-12)            │
│                                                             │
│   while current_date < target_date:  ← LESS THAN           │
│                                                             │
│     Day 1: 2025-03-01 < 2025-03-12 → TRUE                  │
│       advance_day() → 2025-03-02                            │
│                                                             │
│     Day 2: 2025-03-02 < 2025-03-12 → TRUE                  │
│       advance_day() → 2025-03-03                            │
│                                                             │
│     ...                                                     │
│                                                             │
│     Day 11: 2025-03-11 < 2025-03-12 → TRUE                 │
│       advance_day() → 2025-03-12                            │
│                                                             │
│     Day 12: 2025-03-12 < 2025-03-12 → FALSE                │
│       ✅ EXIT LOOP                                          │
│                                                             │
│   Final Date: 2025-03-12  ← ON MILESTONE                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   RESULT RETURNED                           │
│         {                                                   │
│           success: true,                                    │
│           days_advanced: 11,                                │
│           date: "2025-03-12",                               │
│           milestone: {                                      │
│             name: "Franchise Tag Deadline",                 │
│             date: "2025-03-12"                              │
│           }                                                 │
│         }                                                   │
└─────────────────────────────────────────────────────────────┘
```

### Milestone Stopping Verification

**Question:** Does it stop ON the milestone or AFTER?

**Analysis:**
```python
# Loop condition: while current_date < target_date

# Example: Milestone on 2025-03-12, currently 2025-03-11

# Iteration 1:
#   Check: 2025-03-11 < 2025-03-12 → TRUE
#   Execute: advance_day() → calendar = 2025-03-12
#   Continue loop

# Iteration 2:
#   Check: 2025-03-12 < 2025-03-12 → FALSE
#   Exit loop immediately

# Final: current_date = 2025-03-12
```

**Verdict:** ✅ **Stops ON milestone, not after.**

Loop uses `<` (less than) comparison, so it stops when `current_date >= target_date`.

---

## Phase Transition Flow

### Dual-Check Pattern

```
┌─────────────────────────────────────────────────────────────┐
│           SeasonCycleController.advance_day()               │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
                    [Calendar Advance]
                   calendar.advance(1)
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│            CHECK #1: Pre-Handler Transition                 │
│            (Date-Based Triggers)                            │
│                                                             │
│  phase_transition = _check_phase_transition()               │
│                                                             │
│  Examples:                                                  │
│  - Offseason → Preseason (calendar reaches preseason start)│
│  - Preseason → Regular Season (calendar reaches week 1)    │
│  - Regular Season → Playoffs (17 weeks complete)           │
│                                                             │
│  if phase_transition:                                       │
│    return immediately (don't execute handler)               │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ [No transition]
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  HANDLER EXECUTION                          │
│          handler.simulate_day(current_date)                 │
│          - Execute phase-specific logic                     │
│          - Process scheduled events                         │
│          - Simulate games (if applicable)                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│            CHECK #2: Post-Handler Transition                │
│            (Game Count or Event-Based Triggers)             │
│                                                             │
│  if not phase_transition:                                   │
│    phase_transition = _check_phase_transition()             │
│                                                             │
│  Examples:                                                  │
│  - Playoffs → Offseason (Super Bowl complete)              │
│  - Preseason → Regular Season (4 preseason games complete) │
│                                                             │
│  Purpose: Catch transitions that depend on games played,   │
│           not just calendar date                           │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
                    [Return Result]
```

### Transition Decision Tree

```
┌───────────────────────────────────────────┐
│ _check_phase_transition()                 │
└─────────────────┬─────────────────────────┘
                  │
                  ▼
      ┌───────────────────────┐
      │  Check Current Phase  │
      └───────────┬───────────┘
                  │
    ┌─────────────┴─────────────┐
    │                           │
    ▼                           ▼
┌─────────┐                ┌─────────┐
│OFFSEASON│                │PRESEASON│
└────┬────┘                └────┬────┘
     │                          │
     │ Check: calendar >=       │ Check: 4 games played?
     │   preseason_start?       │
     │                          │
     │ YES: → PRESEASON         │ YES: → REGULAR_SEASON
     │ NO:  → None              │ NO:  → None
     │                          │
     └──────────────┬───────────┘
                    │
                    ▼
            [Other Phases...]
```

---

## State Persistence Flow

### Current Flow (With ISSUE-001)

```
┌─────────────────────────────────────────────────────────────┐
│     SeasonCycleController.advance_day()                     │
│     Returns: {success: true, date: "2025-03-13", ...}       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│     SimulationController.advance_day()                      │
│                                                             │
│     1. result = season_controller.advance_day()             │
│        ✅ Success, calendar now at 2025-03-13               │
│                                                             │
│     2. new_date = result.get('date')                        │
│        new_date = "2025-03-13"                              │
│                                                             │
│     3. self.current_date_str = new_date                     │
│        ⚠️  UI CACHE UPDATED: "2025-03-13"                   │
│                                                             │
│     4. self._save_state_to_db(new_date, ...)                │
│        ❌ RAISES CalendarSyncPersistenceException            │
│        (Database locked / constraint violation / etc.)      │
│                                                             │
│     5. Exception caught by outer try/except                 │
│        return {success: false, message: "Error: ..."}       │
│                                                             │
│     RESULT:                                                 │
│     - UI cache: "2025-03-13" ❌                             │
│     - Database:  "2025-03-12" ❌                            │
│     - DESYNCHRONIZED                                        │
└─────────────────────────────────────────────────────────────┘
```

### Proposed Flow (ISSUE-001 Fixed)

```
┌─────────────────────────────────────────────────────────────┐
│     SeasonCycleController.advance_day()                     │
│     Returns: {success: true, date: "2025-03-13", ...}       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│     SimulationController.advance_day()                      │
│                                                             │
│     1. result = season_controller.advance_day()             │
│        ✅ Success, calendar now at 2025-03-13               │
│                                                             │
│     2. new_date = result.get('date')                        │
│        new_date = "2025-03-13"                              │
│                                                             │
│     3. self._save_state_to_db(new_date, ...)                │
│        ✅ SAVE FIRST (within transaction)                   │
│        ✅ Database: "2025-03-13"                            │
│                                                             │
│     4. self.current_date_str = new_date                     │
│        ✅ UI CACHE UPDATED AFTER SAVE: "2025-03-13"         │
│                                                             │
│     5. self.date_changed.emit(new_date)                     │
│        ✅ Signals emitted with synchronized state           │
│                                                             │
│     RESULT:                                                 │
│     - UI cache: "2025-03-13" ✅                             │
│     - Database:  "2025-03-13" ✅                            │
│     - SYNCHRONIZED                                          │
│                                                             │
│     Note: If save fails, exception raised BEFORE cache      │
│           update, so cache remains at previous date         │
└─────────────────────────────────────────────────────────────┘
```

### Transaction-Wrapped Persistence (ISSUE-003 Fix)

```
┌─────────────────────────────────────────────────────────────┐
│    SimulationController._save_state_to_db()                 │
│                                                             │
│    with TransactionContext(db_path, 'IMMEDIATE') as ctx:   │
│                                                             │
│      ┌─────────────────────────────────────────────────┐   │
│      │  1. Pre-sync Validation                         │   │
│      │     validator.verify_pre_sync(...)              │   │
│      │     (using ctx.connection)                      │   │
│      │                                                  │   │
│      │  2. Save State                                   │   │
│      │     state_model.save_state(...)                 │   │
│      │     (using ctx.connection)                      │   │
│      │                                                  │   │
│      │     IF FAIL:                                     │   │
│      │       ctx.rollback()                            │   │
│      │       raise CalendarSyncPersistenceException    │   │
│      │                                                  │   │
│      │  3. Post-sync Validation                        │   │
│      │     validator.verify_post_sync(...)             │   │
│      │     (using ctx.connection)                      │   │
│      │                                                  │   │
│      │     IF FAIL:                                     │   │
│      │       ctx.rollback()                            │   │
│      │       raise CalendarSyncDriftException          │   │
│      │                                                  │   │
│      │  4. Explicit Commit                             │   │
│      │     ctx.commit()                                │   │
│      │     ✅ ATOMIC SUCCESS                            │   │
│      └─────────────────────────────────────────────────┘   │
│                                                             │
│    Benefits:                                                │
│    - All operations use SAME database connection           │
│    - Atomic: ALL succeed or ALL fail                       │
│    - No partial writes on crash                            │
│    - Rollback if ANY step fails                            │
└─────────────────────────────────────────────────────────────┘
```

### Template Method Pattern Flow (ISSUE-002 Fix)

```
┌─────────────────────────────────────────────────────────────┐
│    SimulationController._execute_simulation_with_persistence│
│                                                             │
│    Centralized workflow for all 4 simulation methods:      │
│    - advance_day()                                          │
│    - advance_week()                                         │
│    - advance_to_end_of_phase()                              │
│    - simulate_to_new_season()                               │
│                                                             │
│    ┌─────────────────────────────────────────────────────┐ │
│    │  TRY:                                                │ │
│    │                                                      │ │
│    │    1. Call Backend Method                           │ │
│    │       result = backend_method()                     │ │
│    │       (e.g., season_controller.advance_day())       │ │
│    │                                                      │ │
│    │    2. Check Success                                 │ │
│    │       if result.get('success', False):              │ │
│    │                                                      │ │
│    │    3. Extract State (via hook)                      │ │
│    │       date, phase, week = extractors['extract']()   │ │
│    │                                                      │ │
│    │    4. Update Cache                                  │ │
│    │       self.current_date_str = date                  │ │
│    │                                                      │ │
│    │    5. Pre-Save Hook (method-specific)               │ │
│    │       if hooks.get('pre_save'):                     │ │
│    │         hooks['pre_save'](result)                   │ │
│    │       Examples:                                      │ │
│    │       - advance_day: phase transition check         │ │
│    │       - advance_week: week tracking (DB query)      │ │
│    │       - advance_to_end_of_phase: None               │ │
│    │                                                      │ │
│    │    6. Persist to Database                           │ │
│    │       _save_state_to_db(date, phase, week)          │ │
│    │       ✅ FAIL-LOUD (raises exception on error)      │ │
│    │                                                      │ │
│    │    7. Post-Save Hook (method-specific)              │ │
│    │       if hooks.get('post_save'):                    │ │
│    │         hooks['post_save'](result)                  │ │
│    │       Examples:                                      │ │
│    │       - advance_day: emit date_changed + games      │ │
│    │       - advance_week: emit date_changed only        │ │
│    │       - advance_to_end_of_phase: emit + milestone   │ │
│    │                                                      │ │
│    │    8. Build Success Result                          │ │
│    │       return extractors['build_success'](result)    │ │
│    │                                                      │ │
│    └──────────────────────────────────────────────────────┘ │
│                                                             │
│    ┌─────────────────────────────────────────────────────┐ │
│    │  EXCEPT CalendarSyncPersistenceException:           │ │
│    │  EXCEPT CalendarSyncDriftException:                 │ │
│    │                                                      │ │
│    │    1. Show CalendarSyncRecoveryDialog               │ │
│    │       - Retry: recursively call this method         │ │
│    │       - Reload: revert to database state            │ │
│    │       - Abort: return failure result                │ │
│    │                                                      │ │
│    │    2. Return failure_dict_factory(message)          │ │
│    │                                                      │ │
│    └──────────────────────────────────────────────────────┘ │
│                                                             │
│    ┌─────────────────────────────────────────────────────┐ │
│    │  EXCEPT Exception as e:                             │ │
│    │                                                      │ │
│    │    1. Show QMessageBox.critical()                   │ │
│    │       (Unexpected error dialog)                     │ │
│    │                                                      │ │
│    │    2. Return failure_dict_factory(f"Error: {e}")    │ │
│    │                                                      │ │
│    └──────────────────────────────────────────────────────┘ │
│                                                             │
│    Benefits:                                                │
│    - 74% code duplication eliminated (320 → 156 lines)     │
│    - Single source of truth for exception handling         │
│    - Consistent recovery dialog across all methods         │
│    - Hook pattern allows method-specific customization     │
│    - 25/25 tests validate all edge cases                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Interaction Diagram

### Layer Responsibilities

```
┌─────────────────────────────────────────────────────────────────────┐
│                        UI LAYER (PySide6/Qt)                        │
│  ┌────────────────────┐         ┌──────────────────────────────┐   │
│  │  season_view.py    │         │  simulation_controller.py    │   │
│  │                    │         │                              │   │
│  │  - Button handlers │────────>│  - Thin orchestration        │   │
│  │  - Display updates │         │  - State caching             │   │
│  │  - Signal slots    │<────────│  - Signal emission           │   │
│  └────────────────────┘         │  - Persistence coordination  │   │
│                                 └────────────┬─────────────────┘   │
└──────────────────────────────────────────────┼─────────────────────┘
                                               │
                                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     DOMAIN MODEL LAYER                              │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  simulation_data_model.py                                    │   │
│  │                                                              │   │
│  │  - Owns DynastyStateAPI                                      │   │
│  │  - get_state() → query DB                                    │   │
│  │  - save_state() → persist to DB                              │   │
│  │  - Database is SINGLE SOURCE OF TRUTH                        │   │
│  └────────────────────────────┬─────────────────────────────────┘   │
└────────────────────────────────┼─────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│               SIMULATION ORCHESTRATION LAYER                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  season_cycle_controller.py                                  │   │
│  │                                                              │   │
│  │  - OWNS calendar advancement                                 │   │
│  │  - advance_day() / advance_week()                            │   │
│  │  - Phase transition detection                                │   │
│  │  - Handler coordination                                      │   │
│  │  - Statistics tracking                                       │   │
│  └────────────────────────────┬─────────────────────────────────┘   │
└────────────────────────────────┼─────────────────────────────────────┘
                                 │
                ┌────────────────┴────────────────┐
                │                                 │
                ▼                                 ▼
┌──────────────────────────┐      ┌──────────────────────────┐
│   PHASE HANDLER LAYER    │      │   CALENDAR LAYER         │
│                          │      │                          │
│  - OffseasonHandler      │      │  - calendar_manager.py   │
│  - RegularSeasonHandler  │      │  - advance(days)         │
│  - PlayoffHandler        │      │  - get_current_date()    │
│  - PreseasonHandler      │      │  - READ-ONLY for handlers│
│                          │      │                          │
│  - simulate_day(date)    │      └──────────────────────────┘
│  - READ-ONLY date param  │
└────────────┬─────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    EVENT EXECUTION LAYER                            │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  simulation_executor.py                                      │   │
│  │                                                              │   │
│  │  - Query events for date                                     │   │
│  │  - Execute GameEvent, DeadlineEvent, etc.                    │   │
│  │  - Return events_executed                                    │   │
│  └────────────────────────────┬─────────────────────────────────┘   │
└────────────────────────────────┼─────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       DATABASE LAYER (SQLite)                       │
│                                                                     │
│  - dynasty_state (current_date, current_phase, season)              │
│  - events (scheduled events)                                        │
│  - game_results, player_stats, standings, etc.                      │
│                                                                     │
│  AUTHORITATIVE STATE - All other state is cached/derived           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Call Stack Traces

### Trace 1: Day Advancement (Success Path)

```
[USER CLICK] "Advance Day" button
│
├─ ui/views/season_view.py:250
│  └─ _on_simulate_day()
│     │
│     ├─ ui/controllers/simulation_controller.py:286
│     │  └─ advance_day()
│     │     │
│     │     ├─ src/season/season_cycle_controller.py:531
│     │     │  └─ advance_day()
│     │     │     │
│     │     │     ├─ src/season/season_cycle_controller.py:559
│     │     │     │  └─ _auto_recover_year_from_database()
│     │     │     │
│     │     │     ├─ src/calendar/calendar_manager.py:120
│     │     │     │  └─ calendar.advance(days=1)
│     │     │     │
│     │     │     ├─ src/season/season_cycle_controller.py:588
│     │     │     │  └─ _check_phase_transition()
│     │     │     │
│     │     │     ├─ src/offseason/offseason_handler.py:43
│     │     │     │  └─ handler.simulate_day(current_date)
│     │     │     │     │
│     │     │     │     ├─ src/calendar/simulation_executor.py:80
│     │     │     │     │  └─ simulation_executor.simulate_day()
│     │     │     │     │     │
│     │     │     │     │     ├─ src/events/event_database_api.py:150
│     │     │     │     │     │  └─ get_events_for_date()
│     │     │     │     │     │
│     │     │     │     │     └─ src/events/game_event.py:50
│     │     │     │     │        └─ event.execute()
│     │     │     │     │
│     │     │     │     └─ src/offseason/offseason_controller.py:100
│     │     │     │        └─ offseason_controller.simulate_day()
│     │     │     │
│     │     │     ├─ src/season/season_cycle_controller.py:668
│     │     │     │  └─ _check_phase_transition() [second check]
│     │     │     │
│     │     │     └─ [RETURN result dict]
│     │     │
│     │     ├─ ui/controllers/simulation_controller.py:320
│     │     │  └─ self.current_date_str = new_date  ⚠️ DESYNC RISK
│     │     │
│     │     ├─ ui/controllers/simulation_controller.py:323
│     │     │  └─ _save_state_to_db()
│     │     │     │
│     │     │     ├─ ui/domain_models/simulation_data_model.py:101
│     │     │     │  └─ state_model.save_state()
│     │     │     │     │
│     │     │     │     └─ src/database/dynasty_state_api.py:80
│     │     │     │        └─ dynasty_api.save_current_state()
│     │     │     │
│     │     │     └─ ui/controllers/simulation_controller.py:244
│     │     │        └─ validator.verify_post_sync()
│     │     │
│     │     ├─ ui/controllers/simulation_controller.py:327
│     │     │  └─ self.date_changed.emit(new_date)
│     │     │
│     │     └─ [RETURN result]
│     │
│     └─ ui/views/season_view.py:260
│        └─ [Update UI display]
│
[UI UPDATED]
```

### Trace 2: Milestone Simulation

```
[USER CLICK] "Simulate to Next Milestone" button
│
├─ ui/views/season_view.py:300
│  └─ _on_simulate_to_milestone()
│     │
│     ├─ src/season/season_cycle_controller.py:895
│     │  └─ simulate_to_next_offseason_milestone()
│     │     │
│     │     ├─ src/database/event_database_api.py:200
│     │     │  └─ db.events_get_next_offseason_milestone()
│     │     │     [Query: next milestone after current_date]
│     │     │     [Result: 2025-03-12 "Franchise Tag Deadline"]
│     │     │
│     │     ├─ src/season/season_cycle_controller.py:1028
│     │     │  └─ simulate_to_date(target_date=2025-03-12)
│     │     │     │
│     │     │     ├─ [LOOP: while current_date < target_date]
│     │     │     │  │
│     │     │     │  ├─ Day 1: 2025-03-01 < 2025-03-12 → TRUE
│     │     │     │  │  └─ advance_day() [recursive call]
│     │     │     │  │
│     │     │     │  ├─ Day 2: 2025-03-02 < 2025-03-12 → TRUE
│     │     │     │  │  └─ advance_day() [recursive call]
│     │     │     │  │
│     │     │     │  ...
│     │     │     │  │
│     │     │     │  ├─ Day 11: 2025-03-11 < 2025-03-12 → TRUE
│     │     │     │  │  └─ advance_day() [recursive call]
│     │     │     │  │     [Calendar advances to 2025-03-12]
│     │     │     │  │
│     │     │     │  └─ Day 12: 2025-03-12 < 2025-03-12 → FALSE
│     │     │     │     [EXIT LOOP]
│     │     │     │
│     │     │     └─ [RETURN result: days_advanced=11]
│     │     │
│     │     └─ [Add milestone info to result]
│     │
│     └─ [RETURN to UI]
│
[UI UPDATED - Show milestone reached dialog]
```

---

## Legend

```
┌─────────┐
│  Box    │  Component or layer
└─────────┘

    │
    ▼        Flow direction

    ├─       Branch in flow

[Action]     Specific action or decision

✅           Success / Correct behavior
❌           Error / Incorrect behavior
⚠️           Warning / Risk

→            Function call or delegation
←            Return value

READ-ONLY    Parameter passed without modification
OWNS         Component has exclusive write access
```

---

**Document Version:** 1.1
**Last Updated:** November 23, 2025 (ISSUE-002 Template Method Pattern integration)
**Related:** [Main Audit Report](simulation_execution_flow_audit.md) | [Issues Tracker](issues_tracker.md)
