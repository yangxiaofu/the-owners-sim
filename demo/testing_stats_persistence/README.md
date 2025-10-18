# Testing Stats Persistence

This directory contains test scripts for verifying that game statistics, particularly touchdowns, are correctly accumulated and persisted to the database.

## Purpose

The TD persistence issue required a fix to the data flow in `GameLoopController`. These tests verify that:

1. **TD Attribution**: DriveManager correctly adds TDs to player stats when touchdowns are scored
2. **Stats Accumulation**: PlayerStatsAccumulator includes TDs when copying stats from PlayStatsSummary
3. **Database Persistence**: TD stats are correctly saved to the database

## Test Scripts

### `test_td_persistence.py`

Complete end-to-end test of the TD persistence flow.

**Run**: `PYTHONPATH=src python demo/testing_stats_persistence/test_td_persistence.py`

**What it tests**:
- Runs a full game simulation (Detroit Lions @ Green Bay Packers)
- Monitors DriveManager TD attribution messages
- Checks PlayerStatsAccumulator for accumulated TD stats
- Queries database to verify TD persistence
- Provides detailed reporting at each stage

**Expected Output**:
```
✅ DriveManager: Added passing TD to [Player Name]
✅ DriveManager: Added receiving TD to [Player Name]
...
✅ SUCCESS: TDs are being accumulated correctly!
   Total TDs in PlayerStatsAccumulator: 8
   - Passing TDs: 3
   - Rushing TDs: 2
   - Receiving TDs: 3
```

## The Fix

### Problem
TDs were being added by DriveManager but not persisting because stats were recorded to PlayerStatsAccumulator **before** DriveManager added the TDs.

### Solution
Moved stats recording in `GameLoopController._run_drive()` to **after** `drive_manager.process_play_result()` so TDs are included when stats are copied.

**Before**:
```python
# _run_play()
play_result = simulate()
stats_aggregator.record_play_result(play_result)  # TDs = 0
return play_result

# _run_drive()
play_result = _run_play()
drive_manager.process_play_result(play_result)  # Adds TDs (too late!)
```

**After**:
```python
# _run_play()
play_result = simulate()
return play_result  # No stats recording here

# _run_drive()
play_result = _run_play()
drive_manager.process_play_result(play_result)  # Adds TDs first
stats_aggregator.record_play_result(play_result)  # Now TDs are included!
```

## Database Schema

Test uses `test_game.db` with dynasty `test_td_persistence`.

Key table: `player_game_stats`
- `passing_tds` - Passing touchdowns
- `rushing_tds` - Rushing touchdowns
- `receiving_tds` - Receiving touchdowns

## Troubleshooting

### No TDs in PlayerStatsAccumulator
- Check that DriveManager TD attribution messages appear
- Verify stats recording happens AFTER drive processing

### TDs in accumulator but not database
- Check if persistence is enabled
- Verify database connection and table schema
- Check if persistence layer is calling the correct API

### No DriveManager messages
- Ensure game is scoring touchdowns (run multiple times)
- Check if DriveManager._update_touchdown_attribution() is being called
