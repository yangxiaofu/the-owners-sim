# Playoff Scheduler Duplicate Prevention Note

## Potential Secondary Issue

I noticed that `playoff_controller.py` has a method `_reschedule_brackets_from_completed_games()` (lines 819-929) that re-calls `schedule_wild_card_round()` when reconstructing brackets from existing events.

### The Code

**Location**: `src/playoff_system/playoff_controller.py:855-861`

```python
wc_result = self.playoff_scheduler.schedule_wild_card_round(
    seeding=self.original_seeding,
    start_date=wc_start_date,
    season=self.season_year,
    dynasty_id=self.dynasty_id
)
self.brackets['wild_card'] = wc_result['bracket']
```

### The Concern

**If `PlayoffScheduler.schedule_wild_card_round()` doesn't check for existing events**, this will create duplicates when:
1. Existing playoff games are found
2. Bracket is reconstructed from database
3. `_reschedule_brackets_from_completed_games()` is called
4. It calls `schedule_wild_card_round()` again
5. This creates NEW events on top of existing ones

### Two Possible Solutions

#### Option 1: Add Duplicate Check to PlayoffScheduler

Add existence check in `playoff_scheduler.py::schedule_wild_card_round()`:

```python
def schedule_wild_card_round(self, seeding, start_date, season, dynasty_id):
    # Check if events already exist
    event_prefix = f"playoff_{dynasty_id}_{season}_wild_card_"
    existing_events = self.event_db_api.get_events_by_game_id_prefix(
        event_prefix,
        event_type="GAME"
    )

    if existing_events:
        # Events already exist, return bracket structure only
        bracket = self.playoff_manager.generate_wild_card_bracket(
            seeding=seeding,
            start_date=start_date,
            season=season
        )
        return {
            'bracket': bracket,
            'event_ids': [e['event_id'] for e in existing_events],
            'games_scheduled': 0  # No new games scheduled
        }

    # Continue with normal scheduling...
```

**Pros**:
- Scheduler becomes idempotent (safe to call multiple times)
- Prevents duplicates at the source
- Works for all callers

**Cons**:
- Changes scheduler contract (might affect other code)
- Need to handle "bracket-only" return case

#### Option 2: Separate Bracket Generation from Event Scheduling

Split into two methods:
- `generate_wild_card_bracket()` - Creates bracket structure only
- `schedule_wild_card_round()` - Creates bracket AND schedules events

Then `_reschedule_brackets_from_completed_games()` calls generate instead of schedule:

```python
# Instead of:
wc_result = self.playoff_scheduler.schedule_wild_card_round(...)

# Use:
wc_bracket = self.playoff_scheduler.generate_wild_card_bracket_structure(
    seeding=self.original_seeding,
    start_date=wc_start_date,
    season=self.season_year
)
self.brackets['wild_card'] = wc_bracket
```

**Pros**:
- Clear separation of concerns
- No duplicate events
- Scheduler keeps its original contract

**Cons**:
- Requires new method
- More code changes

### Recommendation

**I recommend Option 1** (add duplicate check to scheduler) because:
1. Makes scheduler idempotent and safer
2. Prevents duplicates from any caller, not just this one
3. Matches the pattern already used in `_schedule_next_round()` (line 1040-1054)
4. Minimal disruption to existing code

### How to Verify If This Is an Issue

Run this SQL query after reloading mid-playoffs:

```sql
SELECT
    event_id,
    COUNT(*) as occurrences
FROM events
WHERE event_id LIKE 'playoff_%_wild_card_%'
GROUP BY event_id
HAVING COUNT(*) > 1;
```

If you see any results, `_reschedule_brackets_from_completed_games()` is creating duplicates.

### Note

This is a **separate issue** from the season_cycle_controller bug that was just fixed. The season_cycle_controller fix prevents duplicates from that location, but this note is about preventing them from the `_reschedule_brackets_from_completed_games()` method as well.

You may or may not need this fix depending on whether `schedule_wild_card_round()` already has duplicate protection.

---

**Status**: ⚠️ Potential Issue (Not Confirmed)
**Priority**: Medium (only affects reloads mid-playoffs)
**Date**: 2025-10-12
