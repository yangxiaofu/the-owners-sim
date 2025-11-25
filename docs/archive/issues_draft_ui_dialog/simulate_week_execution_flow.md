# "Simulate Week" Execution Flow - Complete Documentation

**Created**: 2025-11-24
**Purpose**: Comprehensive reference for understanding how the "Simulate Week" button works
**Audience**: Developers and technical users

---

## Quick Summary

When you click "Simulate Week" in the UI, the system attempts to simulate 7 consecutive days of NFL activity (games, events, transactions). The week can end early if:

1. **Milestone detected** - Draft day, franchise tag deadline, or free agency window detected in the next 7 days (UI-layer detection)
2. **Phase transition** - Regular season ends and playoffs begin
3. **Error occurs** - Database failure or other exception (rare)

**NEW (Nov 2025)**: The system now uses **UI-layer milestone detection** where the UI checks for upcoming milestones BEFORE starting simulation, then simulates up to (but not including) the milestone date. This follows proper MVC separation - the UI handles routing decisions while the backend only simulates.

---

## High-Level Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER CLICKS "SIM WEEK"                       │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 1: UI Main Window                                             │
│  File: ui/main_window.py                                            │
│  Method: _sim_week() [lines 635-705]                                │
│                                                                      │
│  What happens:                                                       │
│  • NEW: Check for milestones in next 7 days (UI-layer detection)   │
│  • If milestone found: simulate up to it, handle, continue          │
│  • If no milestone: simulate full week                              │
│  • Records start date                                                │
│  • Calls simulation_controller.advance_week() or advance_days()     │
│  • Waits for result                                                  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 2: Simulation Controller (UI Layer)                           │
│  File: ui/controllers/simulation_controller.py                      │
│  Method: advance_week() [lines 525-580]                             │
│                                                                      │
│  What happens:                                                       │
│  • Sets up hooks for pre-save and post-save                         │
│  • Delegates to template method                                     │
│  • Calls backend: season_controller.advance_week()                  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 3: Template Method - Persistence Orchestration                │
│  File: ui/controllers/simulation_controller.py                      │
│  Method: _execute_simulation_with_persistence() [lines 298-430]     │
│                                                                      │
│  8-Step Workflow:                                                    │
│  1. Call backend method                                              │
│  2. Extract state (date, phase, week)                               │
│  3. Run pre-save hook                                                │
│  4. ⚠️ SAVE TO DATABASE (CRITICAL!)                                 │
│  5. Update cache                                                     │
│  6. Run post-save hook                                               │
│  7. Build result dict                                                │
│  8. Error handling                                                   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 4: Database Persistence                                        │
│  File: ui/controllers/simulation_controller.py                      │
│  Method: _save_state_to_db() [lines 201-297]                        │
│                                                                      │
│  What happens:                                                       │
│  • Opens database connection                                         │
│  • Wraps in TransactionContext (IMMEDIATE mode)                     │
│  • Calls state_model.save_state()                                   │
│  • Commits transaction                                               │
│  • Runs post-sync verification (detects drift)                      │
│                                                                      │
│  💡 TIP: This is where calendar drift would be prevented            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 5: Backend Week Loop (MAIN LOOP)                              │
│  File: src/season/season_cycle_controller.py                        │
│  Method: advance_week() [lines 942-1044]                            │
│                                                                      │
│  NEW (Nov 2025): Backend NO LONGER checks for milestones!           │
│  Milestone detection moved to UI layer (Step 1)                     │
│                                                                      │
│  FOR EACH OF 7 DAYS:                                                 │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ CHECKPOINT 1: Execute one day                               │   │
│  │ • Call advance_day()                                        │   │
│  │ • Simulate games for this day                               │   │
│  │ • Process events and transactions                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                           │                                          │
│                           ▼                                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ CHECKPOINT 2: Check for phase transition                    │   │
│  │ • If regular season ends → STOP EARLY                       │   │
│  │ • Return phase_transition=True                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  Two ways to exit loop:                                              │
│  1. Phase transition (return phase_transition=True)                 │
│  2. Complete 7 days (return week_complete=True)                     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 6: Daily Simulation                                            │
│  File: src/season/season_cycle_controller.py                        │
│  Method: advance_day() [lines 790-939]                              │
│                                                                      │
│  What happens:                                                       │
│  1. Auto-recovery guard (prevents year drift)                       │
│  2. ⚠️ Advance calendar by 1 day (HAPPENS ONCE!)                   │
│  3. Check phase transition (before handler)                         │
│  4. Get phase handler (strategy pattern)                            │
│  5. Execute handler.simulate_day(current_date)                      │
│  6. Update statistics (games played, days simulated)                │
│  7. Transaction evaluation (AI trades)                              │
│  8. Check phase transition (after handler)                          │
│  9. Return result dict                                               │
│                                                                      │
│  💡 TIP: Calendar advances BEFORE handler executes                  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 8: Phase Handler (Strategy Pattern)                           │
│  File: src/season/phase_handlers/regular_season_handler.py          │
│  Method: simulate_day() [lines 36-71]                               │
│                                                                      │
│  What happens:                                                       │
│  • Calls simulation_executor.simulate_day(current_date)             │
│  • Updates handler statistics                                        │
│  • Returns result dict with games played                             │
│                                                                      │
│  ✅ Handler does NOT advance calendar (already done by controller)  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 9: Event Execution                                             │
│  File: src/calendar/simulation_executor.py                          │
│  Method: simulate_day() [lines 449-546]                             │
│                                                                      │
│  What happens:                                                       │
│  1. Query database for events on target_date                        │
│  2. If no events → return empty result                              │
│  3. Batch simulate all events                                        │
│  4. Separate games from other events                                │
│  5. Return result with games played                                  │
│                                                                      │
│  Event types executed:                                               │
│  • GAME (most common)                                                │
│  • FRANCHISE_TAG                                                     │
│  • PLAYER_RELEASE                                                    │
│  • DEADLINE                                                          │
│  • And more...                                                       │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 10: Game Simulation                                            │
│  (If games scheduled for this day)                                   │
│                                                                      │
│  File: src/game_management/full_game_simulator.py                   │
│  Method: simulate_game()                                             │
│                                                                      │
│  What happens:                                                       │
│  • Simulates full NFL game (4 quarters)                             │
│  • Tracks player statistics                                          │
│  • Updates team statistics                                           │
│  • Determines winner/loser                                           │
│  • Persists results to database                                      │
│                                                                      │
│  Database writes:                                                    │
│  • games table (game result)                                         │
│  • player_stats table (all players)                                 │
│  • team_stats table (both teams)                                    │
│  • standings table (updated records)                                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 11: Result Aggregation                                         │
│  File: src/season/season_cycle_controller.py                        │
│  Method: _aggregate_week_results() [lines 1046-1119]                │
│                                                                      │
│  What happens:                                                       │
│  • Accumulates daily results into weekly summary                    │
│  • Counts total games played                                         │
│  • Collects all game results                                         │
│  • Tracks transactions executed                                      │
│  • Detects phase transitions                                         │
│  • Adds milestone info if detected                                   │
│                                                                      │
│  Returns: Weekly summary dict                                        │
│  {                                                                   │
│    "success": True,                                                  │
│    "week_complete": True,                                            │
│    "current_phase": "REGULAR_SEASON",                               │
│    "phase_transition": False,                                        │
│    "date": "2025-09-14",                                            │
│    "games_played": 14,                                               │
│    "results": [...],                                                 │
│    "milestone_detected": False,                                      │
│    "days_simulated": 7                                               │
│  }                                                                   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 12: Return to UI Controller                                    │
│  File: ui/controllers/simulation_controller.py                      │
│  Method: _execute_simulation_with_persistence() [line 381]          │
│                                                                      │
│  What happens:                                                       │
│  • Backend method completed                                          │
│  • State already saved to database (Step 4)                         │
│  • Success result built and returned to UI                          │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 13: UI Update                                                  │
│  File: ui/main_window.py                                            │
│  Method: _sim_week() [lines 699-704]                                │
│                                                                      │
│  What happens:                                                       │
│  1. Shows completion message with statistics                        │
│  2. Refreshes calendar view                                          │
│  3. Refreshes playoff view (if in playoffs/offseason)               │
│                                                                      │
│  If milestone detected:                                              │
│  • Routes to interactive event handler                              │
│  • Opens draft dialog / franchise tag dialog / etc.                 │
│  • User interacts with dialog                                        │
│  • Simulation paused until dialog closed                            │
└──────────────────────────────┴──────────────────────────────────────┘
```

---

## Simple Step-by-Step Explanation

### Step 1: User Clicks Button
**What Happens**: You click the "Sim Week" button in the UI (either from the menu or toolbar).

**Behind the Scenes**: Qt triggers the `_sim_week()` method in the main window, which records your start date and prepares to simulate 7 days.

**Files Involved**: `ui/main_window.py` (lines 635-705)

---

### Step 2: Controller Takes Over
**What Happens**: The UI hands off control to the simulation controller.

**Behind the Scenes**: The controller sets up "hooks" - special functions that will run before and after saving to the database. These hooks emit signals to update the UI.

**Files Involved**: `ui/controllers/simulation_controller.py` (lines 525-580)

**Analogy**: Think of this like a manager delegating a task to a worker, but giving the worker specific instructions on what to report back when done.

---

### Step 3: Persistence Template Runs
**What Happens**: A standardized 8-step workflow executes.

**Behind the Scenes**:
1. Calls the backend simulation
2. Extracts the new date/phase/week from the result
3. Runs pre-save hook (emits phase change signals if needed)
4. **SAVES TO DATABASE** ← This is critical!
5. Updates in-memory cache
6. Runs post-save hook (emits date changed signal)
7. Builds final result dict
8. Catches any errors and shows recovery dialog

**Files Involved**: `ui/controllers/simulation_controller.py` (lines 298-430)

**Why It Matters**: Database save happens BEFORE cache update. This prevents the "calendar drift" bug where UI and database show different dates.

---

### Step 4: Database Write Happens
**What Happens**: The new date, phase, and week get saved to SQLite database.

**Behind the Scenes**:
- Opens database connection
- Wraps save in a transaction (IMMEDIATE mode)
- Calls the database API to write to `dynasty_state` table
- Commits transaction if successful
- Runs verification check to detect any drift
- If any step fails, raises an exception (fail-loud philosophy)

**Files Involved**: `ui/controllers/simulation_controller.py` (lines 201-297)

**Database Table**: `dynasty_state` (columns: dynasty_id, current_date, current_phase, current_week)

**Why It Matters**: This is where calendar drift would be prevented. The old system would fail silently, causing UI and database to desync. New system raises exceptions immediately.

---

### Step 5: Week Loop Starts
**What Happens**: The backend attempts to simulate up to 7 days.

**Behind the Scenes**: A for loop runs from day 0 to day 6. On each iteration:

1. **CHECKPOINT 1**: Check if TOMORROW has a milestone event (draft, deadline, free agency)
   - If yes → Advance calendar TO milestone date, STOP loop early, return milestone info
   - If no → Continue

2. **CHECKPOINT 2**: Execute one day of simulation
   - Advance calendar by 1 day
   - Simulate games scheduled for today
   - Process events and transactions
   - Store daily results

3. **CHECKPOINT 3**: Check if phase transition occurred (e.g., regular season ended)
   - If yes → STOP loop early, return phase_transition=True
   - If no → Continue to next day

**Files Involved**: `src/season/season_cycle_controller.py` (lines 942-1044)

**Three Exit Conditions**:
- Milestone detected → Stop early (milestone_detected=True)
- Phase transition → Stop early (phase_transition=True)
- 7 days complete → Normal completion (week_complete=True)

---

### Step 6: Milestone Detection (Critical!)
**What Happens**: Before each day, system checks if TOMORROW is a special interactive event.

**Behind the Scenes**:
1. Only runs if in OFFSEASON phase
2. Calculates tomorrow's date: `next_date = current_date + 1 day`
3. Queries database for events scheduled on `next_date`
4. Checks for interactive event types:
   - `DRAFT_DAY` (April 24)
   - `DEADLINE` (Franchise Tag Deadline, Roster Cuts Deadline, Cap Compliance)
   - `WINDOW` (Free Agency Opening)
5. Verifies event hasn't been executed yet (checks for `'results'` key in event data)
6. If interactive event found → Returns event dict
7. If no interactive event → Returns None (continue simulating)

**Files Involved**: `src/season/season_cycle_controller.py` (lines 532-643)

**⚠️ CRITICAL CONCEPT - Look-Ahead Pattern**:
- Checks TOMORROW, not TODAY
- This stops the simulation BEFORE the milestone
- Week advances TO the milestone date but doesn't simulate it
- Allows user to interact with the event through a dialog

**Example**:
- Week starts: Jan 1
- Day 1 (Jan 1): Check Jan 2 → No milestone → Simulate Jan 1 normally
- Day 2 (Jan 2): Check Jan 3 → No milestone → Simulate Jan 2 normally
- Day 3 (Jan 3): Check Jan 4 → **DRAFT_DAY FOUND!** → Stop simulation
- Calendar advances to Jan 4 (the milestone date)
- Does NOT simulate Jan 4
- Returns `milestone_detected=True` to UI
- UI opens draft dialog for user interaction

---

### Step 7: Daily Simulation
**What Happens**: If no milestone detected, one day gets simulated.

**Behind the Scenes**:
1. **Auto-recovery guard**: Checks if season_year drifted from database, fixes if needed
2. **Advance calendar**: Increments current date by 1 day ← **HAPPENS ONCE PER DAY**
3. **Phase transition check (before)**: Sees if we're about to cross a phase boundary
4. **Get phase handler**: Uses strategy pattern to select appropriate handler (RegularSeasonHandler, PlayoffHandler, OffseasonHandler)
5. **Execute handler**: Calls `handler.simulate_day(current_date)`
6. **Update statistics**: Increments total games played, days simulated counters
7. **Transaction evaluation**: AI teams check if they should propose trades (if allowed in current phase)
8. **Phase transition check (after)**: Sees if handler triggered a phase transition
9. **Return result**: Dict with games played, transactions, phase info

**Files Involved**: `src/season/season_cycle_controller.py` (lines 790-939)

**✅ Important**: Calendar advances BEFORE handler executes. Handler does NOT advance calendar again (this was a bug in the past).

---

### Step 8: Phase Handler Executes
**What Happens**: The appropriate handler for the current phase simulates the day.

**Behind the Scenes**:
- **RegularSeasonHandler**: Simulates games scheduled for this day
- **PlayoffHandler**: Simulates playoff games (Wild Card, Divisional, Conference, Super Bowl)
- **OffseasonHandler**: Executes offseason events (trades, signings, releases)

For regular season (most common):
1. Calls `simulation_executor.simulate_day(current_date)`
2. Updates handler statistics (games played, days simulated)
3. Returns result dict with games played and standings info

**Files Involved**: `src/season/phase_handlers/regular_season_handler.py` (lines 36-71)

**✅ Handler does NOT advance calendar** - controller already did that in Step 7!

---

### Step 9: Event Execution
**What Happens**: The system looks up what events are scheduled for today and executes them.

**Behind the Scenes**:
1. Queries database: `SELECT * FROM events WHERE event_date = 'YYYY-MM-DD'`
2. If no events found → Returns empty result (no games today)
3. If events found → Batch simulates all events:
   - **GAME events**: Full NFL game simulation
   - **FRANCHISE_TAG events**: Player gets tagged
   - **PLAYER_RELEASE events**: Player released, cap hit calculated
   - **DEADLINE events**: Check compliance (franchise tag deadline, cap deadline, etc.)
4. Separates games from non-game events
5. Returns result dict with games played, events executed

**Files Involved**: `src/calendar/simulation_executor.py` (lines 449-546)

**Database Tables Queried**:
- `events` - All events for this dynasty and date

---

### Step 10: Game Simulation (If Games Scheduled)
**What Happens**: If there are NFL games scheduled today, each game gets fully simulated.

**Behind the Scenes**:
- Full 4-quarter NFL game simulation
- Play-by-play execution (run plays, pass plays, field goals, etc.)
- Player statistics tracked (passing yards, rushing yards, tackles, etc.)
- Team statistics updated (total yards, first downs, time of possession)
- Winner/loser determined
- Results persisted to database

**Files Involved**: `src/game_management/full_game_simulator.py`

**Database Writes (per game)**:
- `games` table: Game result (winner, loser, scores)
- `player_stats` table: ~50-60 rows (all players who participated)
- `team_stats` table: 2 rows (both teams)
- `standings` table: 2 updates (both teams' records)

**Typical Regular Season Week**: 14-16 games (half the league plays)

---

### Step 11: Result Aggregation
**What Happens**: After 1-7 days are simulated, the backend collects all the results into a summary.

**Behind the Scenes**:
- Loops through all daily results
- Counts total games played
- Collects all game results into one list
- Tracks all transactions executed
- Tracks all events triggered
- Checks if phase transition occurred
- Checks if milestone was detected
- Builds message string (e.g., "Simulated 7 days, 14 games played")

**Files Involved**: `src/season/season_cycle_controller.py` (lines 1046-1119)

**Returns Dict Structure**:
```python
{
    "success": True,
    "week_complete": True,  # False if stopped early
    "current_phase": "REGULAR_SEASON",
    "phase_transition": False,
    "date": "2025-09-14",
    "games_played": 14,
    "results": [...],  # All game results
    "transactions_executed": [...],
    "events_triggered": [...],
    "milestone_detected": False,  # True if draft/deadline found
    "milestone_type": None,  # "DRAFT_DAY" if detected
    "milestone_date": None,  # "2025-04-24" if detected
    "days_simulated": 7,
    "message": "Simulated 7 days, 14 games played"
}
```

---

### Step 12: Return to UI Controller
**What Happens**: The backend is done, result gets passed back to the UI controller.

**Behind the Scenes**:
- Template method receives backend result
- State was already saved to database (Step 4)
- Signals were already emitted (Step 3, post-save hook)
- Final result dict built and returned to main window

**Files Involved**: `ui/controllers/simulation_controller.py` (line 381)

---

### Step 13: UI Updates
**What Happens**: The UI refreshes to show the new state.

**Behind the Scenes**:

**Normal completion (no milestone)**:
1. Shows completion message: "Successfully simulated 7 days, 14 games played"
2. Refreshes calendar view (shows new date)
3. If in playoffs/offseason, refreshes playoff bracket view

**Milestone detected**:
1. Routes to interactive event handler based on milestone type
2. Opens appropriate dialog:
   - `DRAFT_DAY` → Draft dialog (user makes picks)
   - `DEADLINE` (Franchise Tag) → Franchise tag dialog
   - `WINDOW` (Free Agency) → Free agency dashboard
3. User interacts with dialog
4. Dialog closes when complete
5. Event marked as executed in database
6. Shows completion message

**Files Involved**: `ui/main_window.py` (lines 699-704 for normal completion, lines 653-679 for milestone routing)

**UI Components Updated**:
- Calendar view: Shows new date
- Week number display: Updated
- Status bar: May show milestone info
- Playoff view: Refreshed if in playoffs
- Standings view: Implicitly updated (queries database)

---

## Three Execution Paths in Detail

### Path 1: Normal Week Completion (7 Days)

**Scenario**: No milestones, no phase transitions, just 7 regular days

**Flow**:
```
UI → Controller → Backend Week Loop (7 iterations) →
  Daily Simulation × 7 →
  Phase Handler × 7 →
  Event Execution × 7 →
  Game Simulation × N games →
  Aggregate Results →
  Save to DB (once) →
  Return to UI →
  Refresh Views
```

**Example Timeline**:
- **Day 1 (Sept 8)**: Simulate → 14 games played
- **Day 2 (Sept 9)**: Simulate → 0 games (Monday, no games)
- **Day 3 (Sept 10)**: Simulate → 1 game (Tuesday night)
- **Day 4 (Sept 11)**: Simulate → 0 games
- **Day 5 (Sept 12)**: Simulate → 0 games
- **Day 6 (Sept 13)**: Simulate → 0 games
- **Day 7 (Sept 14)**: Simulate → 0 games
- **Total**: 7 days, 15 games

**Database Operations**:
- **Reads**: ~20-30 (event queries, schedule queries)
- **Writes**: ~150-200 (1 state write + 15 games × ~10 writes each)

**Duration**: 2-5 seconds typical

**Result**:
```python
{
    "success": True,
    "week_complete": True,
    "days_simulated": 7,
    "games_played": 15,
    "milestone_detected": False
}
```

---

### Path 2: Milestone Detection (Draft Day Example)

**Scenario**: Simulating a week that includes April 24 (Draft Day)

**Flow**:
```
UI → Controller → Backend Week Loop (1-6 iterations) →
  Day 1: Check April 22 → No milestone → Simulate April 21 →
  Day 2: Check April 23 → No milestone → Simulate April 22 →
  Day 3: Check April 24 → DRAFT_DAY MILESTONE FOUND! →
    Advance calendar to April 24 →
    STOP (don't simulate April 24) →
    Return milestone_detected=True →
  Save to DB →
  Return to UI →
  UI Opens Draft Dialog →
  User Makes Picks →
  Dialog Closes →
  Event Marked Executed
```

**Example Timeline**:
- **April 21**: Week starts, check April 22 → No milestone → Simulate April 21
- **April 22**: Check April 23 → No milestone → Simulate April 22
- **April 23**: Check April 24 → **DRAFT DAY FOUND!** → Advance to April 24, STOP
- Calendar now shows **April 24** but hasn't simulated it yet
- Draft dialog opens
- User interacts with draft
- Draft completes, dialog closes
- Event marked executed
- User can continue simulation from April 25

**⚠️ Key Point**: System stops ON the milestone date WITHOUT simulating it. This gives the user a chance to interact with the event.

**Database Operations**:
- **Reads**: ~10 (2-3 days of event queries + milestone check)
- **Writes**: ~5 (1 state write + event marking)

**Duration**: 1-2 seconds simulation + user interaction time

**Result**:
```python
{
    "success": True,
    "week_complete": False,  # Stopped early!
    "days_simulated": 3,  # Only simulated 3 days
    "games_played": 0,  # No games in offseason
    "milestone_detected": True,
    "milestone_type": "DRAFT_DAY",
    "milestone_date": "2025-04-24"
}
```

---

### Path 3: Phase Transition (Regular Season Ends)

**Scenario**: Week includes the last game of regular season (game 272)

**Flow**:
```
UI → Controller → Backend Week Loop (1-7 iterations) →
  Day 1-3: Simulate normally →
  Day 4: Simulate → 272nd game played →
    Handler detects phase transition →
    Sets phase_transition flag →
    Returns →
  Backend checks phase_transition flag →
  STOP (don't continue to day 5-7) →
  Aggregate results →
  Save to DB →
  Return phase_transition=True →
  UI Refreshes (now shows PLAYOFFS phase)
```

**Example Timeline**:
- **Day 1 (Jan 6)**: Simulate → 14 games (256-269)
- **Day 2 (Jan 7)**: Simulate → 0 games
- **Day 3 (Jan 8)**: Simulate → 3 games (270-272) → **272nd game triggers phase transition**
- Regular season COMPLETE
- Phase changes: REGULAR_SEASON → PLAYOFFS
- Week STOPS (days 4-7 not simulated)
- Calendar shows Jan 8 (3 days simulated, not 7)

**Database Operations**:
- **Reads**: ~15 (3 days of event queries)
- **Writes**: ~100 (1 state write + ~30 games × 3 writes each)

**Duration**: 1-3 seconds

**Result**:
```python
{
    "success": True,
    "week_complete": False,  # Stopped early!
    "days_simulated": 3,
    "games_played": 17,
    "phase_transition": True,
    "current_phase": "PLAYOFFS"  # Changed from REGULAR_SEASON
}
```

---

## Draft Detection - Deep Dive

### When Is Draft Detected?

**Detection Point**: Inside the week loop, BEFORE each day

**File**: `src/season/season_cycle_controller.py`
**Method**: `_check_for_milestone_on_next_date()` (lines 532-643)
**Called From**: `advance_week()` loop (line 983)

### Detection Logic (Pseudocode)

```python
def _check_for_milestone_on_next_date():
    # Step 1: Only check in offseason
    if current_phase != OFFSEASON:
        return None

    # Step 2: Calculate TOMORROW's date
    next_date = current_date.add_days(1)

    # Step 3: Query database for events on TOMORROW
    events = query_database(
        "SELECT * FROM events WHERE event_date = ? AND dynasty_id = ?",
        next_date, dynasty_id
    )

    # Step 4: Check each event
    for event in events:
        # Check for DRAFT_DAY
        if event['event_type'] == 'DRAFT_DAY':
            # Check if not already executed
            if 'results' not in event['data']:
                # MILESTONE FOUND!
                return event

        # Check for DEADLINE
        if event['event_type'] == 'DEADLINE':
            if 'results' not in event['data']:
                return event

        # Check for WINDOW (Free Agency)
        if event['event_type'] == 'WINDOW':
            if 'results' not in event['data']:
                return event

    # No milestone found
    return None
```

### Why Check Tomorrow's Date?

**Problem**: If we checked TODAY's date, the system would:
1. Simulate today normally
2. Execute the draft event as part of today's simulation
3. User wouldn't get a chance to interact

**Solution**: Check TOMORROW's date
1. See draft is scheduled for tomorrow
2. STOP simulation before tomorrow
3. Advance calendar TO tomorrow (but don't simulate)
4. Open dialog for user interaction
5. User completes draft
6. Mark event as executed
7. Continue simulation from the day after

**Example**:
```
Current date: April 23
Check for milestone on: April 24 (tomorrow)
Query returns: DRAFT_DAY event for April 24
Action: Advance calendar to April 24, STOP, open dialog
Result: User drafts on April 24, continues from April 25
```

### How Is Draft Scheduled?

**File**: `src/offseason/offseason_event_scheduler.py`
**Method**: `_schedule_milestone_events()` (lines 440-454)

**Code**:
```python
# Draft Day (Late April)
draft_day_date = self._calculate_offseason_date(season_year, month=4, day=24)
draft_day_event = DraftDayEvent(
    event_id=self.db.generate_event_id(),
    event_date=draft_day_date,
    dynasty_id=self.dynasty_id,
    season_year=season_year,
    user_team_id=1,  # Fallback, dynamically fetched later
    description="NFL Draft (7 Rounds, 262 Picks)"
)
self.db.save_event(draft_day_event)
```

**When**: Called during offseason initialization (after Super Bowl)
**Date**: April 24 of the current season year
**Database**: Saved to `events` table with `event_type='DRAFT_DAY'`

### Verification Draft Was Detected

**Console Output**:
```
[MILESTONE CHECK] Checking for milestone on next date: 2025-04-24
[MILESTONE CHECK] Found 1 events for date 2025-04-24
[MILESTONE CHECK] Checking event: DRAFT_DAY
[MILESTONE CHECK] ✅ Returning DRAFT_DAY milestone!
[WEEK LOOP] Milestone detected! Stopping weekly simulation.
[WEEK LOOP] Calendar advanced to milestone date: 2025-04-24
```

**Database Query**:
```sql
-- Check if draft event exists
SELECT event_id, event_type, event_date, data
FROM events
WHERE dynasty_id = 'your_dynasty'
  AND event_type = 'DRAFT_DAY'
  AND event_date = '2025-04-24';

-- Check if already executed (has results)
-- If data column contains {"results": ...}, it's already done
```

---

## Database Operations Summary

### Read Operations (Per Week)

**events table**: 7 queries (one per day)
```sql
SELECT * FROM events
WHERE event_date = ? AND dynasty_id = ?
ORDER BY event_id;
```

**schedules table**: 1-7 queries (varies by handler)
```sql
SELECT * FROM schedules
WHERE week = ? AND season_year = ?;
```

**dynasty_state table**: Multiple reads (validation checks)
```sql
SELECT current_date, current_phase, current_week, season_year
FROM dynasty_state
WHERE dynasty_id = ?;
```

**Total Reads**: 20-30 per week (varies by games scheduled)

---

### Write Operations (Per Week)

**dynasty_state table**: 1 write (at end of week)
```sql
UPDATE dynasty_state
SET current_date = ?,
    current_phase = ?,
    current_week = ?,
    last_updated = CURRENT_TIMESTAMP
WHERE dynasty_id = ?;
```

**games table**: 1 write per game
```sql
INSERT INTO games (game_id, date, home_team_id, away_team_id, home_score, away_score, ...)
VALUES (?, ?, ?, ?, ?, ?, ...);
```

**player_stats table**: ~50 writes per game (all players)
```sql
INSERT INTO player_stats (player_id, game_id, team_id, position, passing_yards, ...)
VALUES (?, ?, ?, ?, ?, ...);
```

**team_stats table**: 2 writes per game (both teams)
```sql
INSERT INTO team_stats (game_id, team_id, total_yards, first_downs, ...)
VALUES (?, ?, ?, ?, ...);
```

**standings table**: 2 updates per game (both teams)
```sql
UPDATE standings
SET wins = wins + 1,
    points_for = points_for + ?,
    ...
WHERE team_id = ? AND season_year = ?;
```

**Total Writes for Typical Week** (14 games):
- 1 dynasty_state
- 14 games
- ~700 player_stats (50 players × 14 games)
- 28 team_stats (2 teams × 14 games)
- 28 standings updates (2 teams × 14 games)
- **Total**: ~771 database writes

---

### Transaction Wrapping

**All writes wrapped in transaction**:
```python
with TransactionContext(connection, mode='IMMEDIATE') as tx:
    # Write dynasty_state
    state_api.save_state(date, phase, week, connection)

    # Commit explicitly
    tx.commit()
# Auto-rollback if any exception
```

**Transaction Modes**:
- `DEFERRED`: Default, acquires lock on first write
- `IMMEDIATE`: Acquires write lock immediately (used for state saves)
- `EXCLUSIVE`: Acquires exclusive lock (rare, used for migrations)

---

## Signal Emissions

Signals are Qt's mechanism for notifying the UI about backend changes.

### Signals Emitted During Week Simulation

**1. `date_changed` Signal**

**Emitter**: `SimulationController`
**File**: `ui/controllers/simulation_controller.py` (line 546)
**When**: After successful database save (post-save hook)
**Frequency**: Once at end of week
**Data**: New date string (e.g., "2025-09-14")

**Connected To**:
- Calendar view (updates date display)
- Main window status bar (updates current date)

**Code**:
```python
def post_save_hook():
    self.date_changed.emit(new_date_str)
```

---

**2. `games_played` Signal**

**Emitter**: `SimulationController`
**File**: `ui/controllers/simulation_controller.py` (line 482)
**When**: After each day if games occurred
**Frequency**: 0-7 times per week (depends on schedule)
**Data**: List of game result dicts

**Connected To**:
- Game view (shows recent games)
- Season view (triggers standings refresh)

**Code**:
```python
def post_save_hook():
    if result.get('games_played', 0) > 0:
        self.games_played.emit(result['results'])
```

---

**3. `phase_changed` Signal**

**Emitter**: `SimulationController`
**File**: `ui/controllers/simulation_controller.py` (line 473)
**When**: During phase transition
**Frequency**: 0-1 times per week (rare)
**Data**: Tuple of (old_phase, new_phase)

**Connected To**:
- Main window (updates phase display)
- Calendar view (updates phase label)
- Season view (may change available actions)

**Code**:
```python
def pre_save_hook():
    if old_phase != new_phase:
        self.phase_changed.emit(old_phase, new_phase)
```

---

### UI Components Listening to Signals

**Calendar View** (`ui/views/calendar_view.py`):
```python
simulation_controller.date_changed.connect(self.refresh_current_date)
simulation_controller.phase_changed.connect(self.update_phase_label)
```

**Season View** (`ui/views/season_view.py`):
```python
simulation_controller.games_played.connect(self.refresh_standings)
```

**Main Window** (`ui/main_window.py`):
```python
simulation_controller.date_changed.connect(self._update_status_bar)
simulation_controller.phase_changed.connect(self._update_phase_display)
```

---

## Common Issues and Debugging

### Issue 1: Draft Not Detected

**Symptoms**: Week simulation passes through April 24 without opening draft dialog

**Possible Causes**:
1. `skip_offseason_events` flag set to `True`
2. Not in `OFFSEASON` phase
3. Draft event not in database
4. Draft event already executed (has `'results'` key)

**Debugging Steps**:

**Check 1: Verify offseason events enabled**
```python
# In season_cycle_controller.py, line 981
print(f"skip_offseason_events: {self.skip_offseason_events}")
# Should be False during normal simulation
```

**Check 2: Verify current phase**
```sql
SELECT current_phase FROM dynasty_state WHERE dynasty_id = 'your_dynasty';
-- Should return 'OFFSEASON' for draft to be detected
```

**Check 3: Verify draft event exists**
```sql
SELECT event_id, event_type, event_date, data
FROM events
WHERE dynasty_id = 'your_dynasty'
  AND event_type = 'DRAFT_DAY';
-- Should return one row with event_date = '2025-04-24'
```

**Check 4: Check if already executed**
```sql
SELECT data FROM events
WHERE dynasty_id = 'your_dynasty'
  AND event_type = 'DRAFT_DAY';
-- If data contains {"results": ...}, draft already done
```

**Console Output to Look For**:
```
[MILESTONE CHECK] Checking for milestone on next date: 2025-04-24
[MILESTONE CHECK] Found 1 events for date 2025-04-24
[MILESTONE CHECK] Checking event: DRAFT_DAY
[MILESTONE CHECK] ✅ Returning DRAFT_DAY milestone!
```

**If Not Seeing This**: Check earlier in logs for phase or skip flag issues

---

### Issue 2: Calendar Drift (UI vs Database Mismatch)

**Symptoms**:
- UI shows one date (e.g., "2025-09-14")
- Database shows different date (e.g., "2025-09-07")
- Difference is cumulative (grows over time)

**Root Cause**: Database save failed silently, but UI cache updated anyway

**Detection**:
```
[ERROR SimulationDataModel] Failed to save dynasty state: ...
[ERROR SimulationController] Failed to write dynasty_state!
```

**Verification**:
```sql
-- Check database date
SELECT current_date FROM dynasty_state WHERE dynasty_id = 'your_dynasty';
-- Compare to UI displayed date
-- If mismatch > 1 day, drift occurred
```

**Recovery**:
1. Note the correct date (from database)
2. Close application
3. Reopen application (will load from database)
4. UI should now match database
5. Investigate what caused the save failure (disk space? permissions? database lock?)

**Prevention**:
- ✅ New system uses fail-loud transactions
- ✅ Post-save verification detects drift immediately
- ✅ Exception raised if drift detected (forces user to fix issue)

---

### Issue 3: Double Advance Bug (Historical)

**Symptoms**: Calendar advances 2 days instead of 1

**Root Cause**: Both controller AND handler advancing calendar

**Fix Applied**:
- Controller advances calendar once (line 838 of season_cycle_controller.py)
- Handler does NOT advance calendar
- This bug no longer exists in current codebase

**If You See This**: Check that handler's `simulate_day()` method doesn't call `self.calendar.advance()`

---

### Issue 4: Phase Transition Not Detected

**Symptoms**: Regular season ends but phase doesn't change to PLAYOFFS

**Possible Causes**:
1. Phase transition check disabled
2. Game count not reaching 272
3. Handler not setting phase transition flag

**Debugging**:

**Check game count**:
```sql
SELECT COUNT(*) FROM games WHERE season_year = 2025 AND dynasty_id = 'your_dynasty';
-- Should be 272 for regular season complete
```

**Check phase transition flag**:
```python
# In season_cycle_controller.py, line 1028
print(f"Phase transition detected: {day_result.get('phase_transition', False)}")
```

**Check handler result**:
```python
# In regular_season_handler.py, line 64
print(f"Games played today: {len(games_played)}")
print(f"Total games so far: {self.games_played}")
```

---

### Issue 5: Games Not Simulating

**Symptoms**: Week simulation completes but no games played

**Possible Causes**:
1. No games scheduled for that week
2. Events table missing game entries
3. Simulation executor not finding events

**Debugging**:

**Check schedule**:
```sql
SELECT week, COUNT(*) as games
FROM schedules
WHERE season_year = 2025
GROUP BY week
ORDER BY week;
-- Should show ~16-17 games per week for weeks 1-18
```

**Check events table**:
```sql
SELECT event_date, COUNT(*) as game_count
FROM events
WHERE event_type = 'GAME'
  AND dynasty_id = 'your_dynasty'
  AND event_date BETWEEN '2025-09-08' AND '2025-09-14'
GROUP BY event_date;
-- Should show games for the week
```

**Console output**:
```
[SIMULATION] Simulating day: 2025-09-08
[SIMULATION] Found 14 events for date 2025-09-08
[SIMULATION] Simulating event batch: 14 events
[SIMULATION] Games played: 14
```

---

## Performance Analysis

### Typical Week (14 games)

**Breakdown**:
- UI button click → Controller: **< 1ms**
- Backend week loop setup: **< 5ms**
- Daily simulation × 7:
  - No games: **~50ms per day** (just event queries)
  - With games: **~300ms per day** (game sim + stats)
- Database persistence: **~200ms** (transaction write)
- UI refresh: **~50ms** (calendar + views)

**Total**: **~2.5 seconds**

**Database Operations**:
- Reads: ~25
- Writes: ~771 (see Database Operations section)

---

### Week with Milestone (Draft)

**Breakdown**:
- UI button click → Controller: **< 1ms**
- Backend week loop: **~500ms** (2-3 days simulated)
- Milestone detection: **< 10ms** (database query)
- Calendar advance: **< 1ms**
- Stop early, return: **< 1ms**
- Database persistence: **~100ms** (smaller write, no games)
- UI opens dialog: **< 100ms**
- **User interaction time**: Variable (minutes to hours)

**Total Simulation Time**: **~700ms** (excluding user interaction)

**Database Operations**:
- Reads: ~10
- Writes: ~5

---

### Phase Transition Week

**Breakdown**:
- UI button click → Controller: **< 1ms**
- Backend week loop: **~1.5 seconds** (3-4 days simulated)
- Games simulation: **~1 second** (17 games typical)
- Phase transition detection: **< 5ms**
- Stop early, return: **< 1ms**
- Database persistence: **~200ms** (state + game writes)
- UI refresh: **~50ms**

**Total**: **~2.8 seconds**

**Database Operations**:
- Reads: ~15
- Writes: ~400

---

## File Reference Quick Map

### UI Layer
| File | Purpose | Key Methods |
|------|---------|-------------|
| `ui/main_window.py` | Main window, button handlers | `_sim_week()` (635-705) |
| `ui/views/calendar_view.py` | Calendar display | `refresh_current_date()` |
| `ui/views/season_view.py` | Standings, schedule | `refresh_standings()` |

### Controller Layer
| File | Purpose | Key Methods |
|------|---------|-------------|
| `ui/controllers/simulation_controller.py` | UI-backend bridge | `advance_week()` (525-580)<br>`_execute_simulation_with_persistence()` (298-430)<br>`_save_state_to_db()` (201-297) |

### Backend Layer
| File | Purpose | Key Methods |
|------|---------|-------------|
| `src/season/season_cycle_controller.py` | Week/day orchestration | `advance_week()` (942-1044)<br>`advance_day()` (790-939)<br>`_check_for_milestone_on_next_date()` (532-643)<br>`_aggregate_week_results()` (1046-1119) |
| `src/season/phase_handlers/regular_season_handler.py` | Regular season logic | `simulate_day()` (36-71) |
| `src/calendar/simulation_executor.py` | Event execution | `simulate_day()` (449-546) |

### Game Simulation
| File | Purpose | Key Methods |
|------|---------|-------------|
| `src/game_management/full_game_simulator.py` | NFL game simulation | `simulate_game()` |
| `src/game_management/game_loop_controller.py` | Game loop | `run_game_loop()` |

### Database
| File | Purpose | Key Methods |
|------|---------|-------------|
| `src/database/dynasty_state_api.py` | Dynasty state CRUD | `save_state()`, `get_dynasty_state()` |
| `src/database/api.py` | Game data access | `save_game()`, `save_player_stats()` |
| `src/database/transaction_context.py` | Transaction wrapper | `__enter__()`, `__exit__()`, `commit()` |

---

## Glossary

**Dynasty**: A saved game / franchise mode save file (like a "career" in sports games)

**Phase**: Current stage of NFL season (PRESEASON, REGULAR_SEASON, PLAYOFFS, OFFSEASON)

**Milestone**: Interactive event requiring user input (draft, franchise tag deadline, free agency)

**Look-Ahead Pattern**: Checking tomorrow's date to detect milestones before simulating them

**Calendar Drift**: Bug where UI and database show different dates (now prevented with fail-loud pattern)

**Phase Transition**: Moving from one phase to another (e.g., regular season → playoffs)

**Handler**: Strategy pattern class that simulates one day based on current phase

**Template Method**: Design pattern providing common workflow with customizable hooks

**Signal**: Qt mechanism for notifying UI components about backend changes

**Transaction Context**: Database wrapper ensuring atomic commits or rollbacks

**Fail-Loud**: Philosophy of raising exceptions immediately instead of silent failure

---

## Conclusion

The "Simulate Week" execution flow is a sophisticated multi-layer system with careful attention to:

- **Data integrity**: Fail-loud database operations prevent silent failures
- **User experience**: Look-ahead milestone detection allows interactive events
- **Performance**: Batch operations and efficient database queries
- **Modularity**: Strategy pattern handlers and template method controllers
- **Debugging**: Comprehensive logging and error handling

Understanding this flow is critical for:
- Implementing Phase 5 (non-modal draft dialog)
- Debugging milestone detection issues
- Adding new interactive events
- Optimizing performance
- Preventing data corruption

---

**Document Version**: 1.0
**Last Updated**: 2025-11-24
**Next Review**: When Phase 5 complete