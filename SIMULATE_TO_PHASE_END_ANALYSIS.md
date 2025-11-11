# simulate_to_phase_end() OLD vs NEW Analysis

## Executive Summary

The NEW code (refactored) is **broken** for preseason→regular season transition because it queries for "first regular season game" from **current date**, but when the current date IS the last preseason game date (August 31), the query finds the FIRST regular season game (September 4), calculates "day before" as September 3, and stops simulation on September 3 - **BEFORE playing the last preseason games on August 31**.

The OLD code worked because it used a **look-ahead loop** that would advance weeks until hitting the stop date, naturally playing all games along the way.

---

## Database Evidence

From `data/database/nfl_simulation.db` (dynasty_id='1st'):

```
Last preseason games:  2025-08-31 16:00:00 | preseason
First regular season:  2025-09-04 20:00:00 | regular_season
```

**Gap between phases: August 31 → September 4 (4 days)**

---

## OLD CODE (Working - commit ee27118)

### Logic Flow

```python
def simulate_to_phase_end(self, progress_callback=None):
    starting_phase = self.phase_state.phase  # PRESEASON

    # Determine next phase
    next_phase_name = "regular_season"

    # Query first game of NEXT phase from current date
    first_game_date = self.event_db.get_first_game_date_of_phase(
        dynasty_id=self.dynasty_id,
        phase_name="regular_season",
        current_date=str(self.calendar.get_current_date())  # e.g., "2025-08-24"
    )
    # Returns: "2025-09-04" (first regular season game)

    # Calculate stop date = day before first game
    first_game_dt = datetime.strptime("2025-09-04", '%Y-%m-%d')
    stop_date_dt = first_game_dt - timedelta(days=1)
    target_stop_date = "2025-09-03"

    # LOOP: Advance week by week until target date
    while True:
        current_date_str = str(self.calendar.get_current_date())  # e.g., "2025-08-24"

        # STOP CONDITION 1: Reached target date
        if current_date_str >= target_stop_date:  # "2025-09-03"
            break

        # Advance one week
        self.advance_week()  # Plays games for week (e.g., Aug 24-30)
        weeks_simulated += 1
```

### Why It Works

1. **Query time**: When current date is "2025-08-24" (Week 3 preseason)
   - Query finds: First regular season game = "2025-09-04"
   - Stop target: "2025-09-03" (day before)

2. **Week advancement loop**:
   - Week 1: advance_week() → plays games Aug 24-30, calendar moves to Aug 31
   - Week 2: advance_week() → plays games Aug 31, calendar moves to Sep 1
   - Week 3: advance_week() → calendar moves to Sep 2, Sep 3
   - **STOP**: current_date >= "2025-09-03"

3. **Result**: All preseason games played (including Aug 31 games)

---

## NEW CODE (Broken - current)

### Logic Flow

```python
def simulate_to_phase_end(self, progress_callback=None):
    starting_phase = self.phase_state.phase  # PRESEASON
    start_date = self.calendar.get_current_date()  # e.g., Date(2025, 8, 31)

    # Get phase end date using _get_phase_end_date()
    phase_end_date = self._get_phase_end_date()

def _get_phase_end_date(self) -> Optional[date]:
    match current_phase:
        case SeasonPhase.PRESEASON:
            # Query first regular season game from CURRENT date
            next_phase_name = "regular_season"
            first_game = self.db.events_get_first_game_date_of_phase(
                phase_name=next_phase_name,
                current_date=str(self.calendar.get_current_date())  # "2025-08-31"
            )
            # Returns: "2025-09-04" (first regular season game)

            # Calculate day before
            first_game_dt = datetime.strptime("2025-09-04", "%Y-%m-%d")
            return (first_game_dt - timedelta(days=1)).date()  # September 3
```

### Query Implementation

```python
# unified_api.py - events_get_first_game_date()
def events_get_first_game_date(self, phase: str, season_year: int, current_date: str):
    # Query for first GAME event in phase on or after current date
    query = """
        SELECT timestamp FROM events
        WHERE dynasty_id = ?
          AND event_type = 'GAME'
          AND json_extract(data, '$.parameters.season_type') = ?
          AND timestamp >= ?  -- On or AFTER current date
          AND json_extract(data, '$.results') IS NULL
        ORDER BY timestamp ASC
        LIMIT 1
    """
```

### Why It Breaks

**Scenario: Current date is August 31 (last preseason game day)**

1. **Query execution**:
   - current_date = "2025-08-31"
   - phase = "regular_season"
   - Query finds: "2025-09-04" (first regular season game)

2. **Stop date calculation**:
   - phase_end_date = September 3 (day before Sep 4)

3. **Days to simulate**:
   - total_days = (Sep 3 - Aug 31) = 2 days

4. **Simulation execution**:
   - Day 1: Advance from Aug 31 → Sep 1
   - Day 2: Advance from Sep 1 → Sep 2
   - **STOP**: Reached Sep 3

5. **PROBLEM**: Games scheduled for August 31 are **NEVER PLAYED**
   - advance_day() is called on Aug 31, which moves calendar forward but doesn't execute games
   - Games only execute when advance_week() processes the full week

---

## Root Cause Analysis

### The Query Problem

The `events_get_first_game_date_of_phase()` query uses:

```sql
AND timestamp >= ?  -- On or AFTER current date
```

This means:
- When current_date = "2025-08-31" (last preseason day)
- Query for "regular_season" finds "2025-09-04"
- Stop date = "2025-09-03"
- **But we haven't played games on Aug 31 yet!**

### The Fundamental Difference

**OLD CODE**:
- Uses **advance_week()** in loop (week-by-week advancement)
- Each week processes ALL games scheduled in that week
- Stops when **calendar date** reaches target
- **Games are played** before calendar advances

**NEW CODE**:
- Uses **advance_day()** in loop (day-by-day advancement)
- Each day advances calendar without necessarily playing games
- Stops when **calendar date** reaches target
- **Games might be skipped** if simulation stops before week completes

---

## Why OLD Didn't Work for Regular Season → Playoffs

The original problem that prompted the refactoring:

```
Regular season ends: Week 18 (around Jan 5)
Playoffs start: Wild Card Weekend (around Jan 11)

Gap: ~6 days between last regular season game and first playoff game
```

**OLD CODE ISSUE**:
- Query "first playoff game" from Jan 5
- Returns Jan 11
- Stop target = Jan 10
- advance_week() keeps simulating full weeks
- **Would advance into playoff week before stopping!**

The OLD code couldn't handle gaps between phases because it used week-based advancement.

---

## Why NEW Doesn't Work for Preseason → Regular Season

```
Preseason ends: August 31
Regular season starts: September 4

Gap: 3 days between last preseason game and first regular season game
```

**NEW CODE ISSUE**:
- When current_date = Aug 31 (last preseason games exist)
- Query "first regular season game" from Aug 31
- Returns Sep 4
- Stop target = Sep 3
- **Simulation stops before playing Aug 31 games!**

The NEW code can't handle same-day games because it queries from current date, not from "after all current phase games complete".

---

## The Correct Solution

The correct logic should be:

1. **Find the LAST game of CURRENT phase** (not first game of next phase)
2. **Stop AFTER that game is played** (not day before next phase starts)

### For Preseason → Regular Season:

```python
# CORRECT:
last_preseason_game = "2025-08-31"
phase_end_date = "2025-08-31"  # Play games on this day, then stop

# WRONG (NEW code):
first_regular_season_game = "2025-09-04"
phase_end_date = "2025-09-03"  # Stops BEFORE playing Aug 31 games
```

### For Regular Season → Playoffs:

```python
# CORRECT:
last_regular_season_game = "2026-01-05"
phase_end_date = "2026-01-05"  # Play games on this day, then stop

# WRONG (OLD code):
first_playoff_game = "2026-01-11"
phase_end_date = "2026-01-10"  # Would advance_week() into playoff week
```

---

## Recommended Fix

### Option A: Query Last Game of Current Phase (Preferred)

```python
def _get_phase_end_date(self) -> Optional[date]:
    current_phase = self.phase_state.phase

    match current_phase:
        case SeasonPhase.PRESEASON:
            # Find LAST preseason game date
            last_game = self.db.events_get_last_game_date_of_phase(
                phase_name="preseason",
                current_date=str(self.calendar.get_current_date())
            )
            if last_game:
                return datetime.strptime(last_game, "%Y-%m-%d").date()
            return None

        case SeasonPhase.REGULAR_SEASON:
            # Find LAST regular season game date
            last_game = self.db.events_get_last_game_date_of_phase(
                phase_name="regular_season",
                current_date=str(self.calendar.get_current_date())
            )
            if last_game:
                return datetime.strptime(last_game, "%Y-%m-%d").date()
            return None
```

**New database query needed**:

```python
# unified_api.py
def events_get_last_game_date_of_phase(self, phase_name: str, current_date: str) -> Optional[str]:
    """Get the date of the LAST game in specified phase (on or after current date)."""
    query = """
        SELECT timestamp FROM events
        WHERE dynasty_id = ?
          AND event_type = 'GAME'
          AND json_extract(data, '$.parameters.season_type') = ?
          AND timestamp >= ?
          AND json_extract(data, '$.results') IS NULL
        ORDER BY timestamp DESC  -- Latest first
        LIMIT 1
    """
    # Returns last game in phase (e.g., "2025-08-31" for preseason)
```

### Option B: Use Boundary Detector for All Phases

The code already uses `PhaseBoundaryDetector` for playoffs and offseason. Extend it to preseason and regular season:

```python
case SeasonPhase.PRESEASON:
    last_preseason_game = self.boundary_detector.get_last_game_date(SeasonPhase.PRESEASON)
    return last_preseason_game.to_python_date() if last_preseason_game else None

case SeasonPhase.REGULAR_SEASON:
    last_regular_season_game = self.boundary_detector.get_last_game_date(SeasonPhase.REGULAR_SEASON)
    return last_regular_season_game.to_python_date() if last_regular_season_game else None
```

---

## Testing Requirements

After fix, verify:

1. **Preseason → Regular Season**:
   - Start: Week 3 preseason (Aug 24)
   - simulate_to_phase_end()
   - Verify: All preseason games played (including Aug 30-31)
   - Verify: Calendar stops on Aug 31 or Sep 1 (NOT Sep 3)
   - Verify: No regular season games played

2. **Regular Season → Playoffs**:
   - Start: Week 17 regular season
   - simulate_to_phase_end()
   - Verify: All Week 18 games played
   - Verify: Calendar stops after Week 18 (around Jan 5)
   - Verify: No playoff games played

3. **Playoffs → Offseason**:
   - Start: Conference Championship
   - simulate_to_phase_end()
   - Verify: Super Bowl played
   - Verify: Calendar stops on Super Bowl date
   - Verify: No offseason events triggered

---

## Summary

| Aspect | OLD Code | NEW Code | Correct Fix |
|--------|----------|----------|-------------|
| **Query** | First game of NEXT phase | First game of NEXT phase | **Last game of CURRENT phase** |
| **Stop Date** | Day before next phase starts | Day before next phase starts | **Last game date of current phase** |
| **Advancement** | advance_week() (week-based) | advance_day() (day-based) | Day-based with correct stop date |
| **Preseason→Regular** | ✅ Works | ❌ Broken | ✅ Will work |
| **Regular→Playoffs** | ❌ Broken | ❌ Broken | ✅ Will work |
| **Playoffs→Offseason** | ✅ Works | ✅ Works | ✅ Will work |

**The fix**: Query for "last game of current phase" instead of "first game of next phase - 1 day".
