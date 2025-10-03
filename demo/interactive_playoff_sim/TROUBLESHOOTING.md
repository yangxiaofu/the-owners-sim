# Playoff Simulation Troubleshooting Guide

## Problem: "Divisional games never simulate"

### Root Cause Identified
After comprehensive testing, we've confirmed that:

✅ **The code is working correctly** - All automated tests pass
✅ **Both dynasty ID formats work** - With and without 'playoff_' prefix
✅ **Event retrieval works** - Double prefix doesn't cause issues
✅ **Game ID parsing works** - Regex handles underscores correctly

**The real issue**: **Stale database from before bug fixes were applied**

### Evidence
The database `demo/interactive_playoff_sim/data/playoffs_2024.db` contains:
- **14 different dynasties** from multiple test runs
- **Only 3 dynasties have Divisional games** (created after fixes)
- **11 dynasties have ONLY Wild Card games** (created before fixes)

If you're in one of the older dynasty sessions, Divisional won't schedule because the scheduling logic was broken when that dynasty was created.

### Solution

#### Option 1: Start a New Dynasty (Recommended)
1. Delete the old database:
   ```bash
   rm demo/interactive_playoff_sim/data/playoffs_2024.db
   ```

2. Run the interactive simulator:
   ```bash
   python demo/interactive_playoff_sim/interactive_playoff_sim.py
   ```

3. When prompted for dynasty name, either:
   - Press Enter for auto-generated (now works correctly)
   - Enter a custom name (avoid starting with "playoff_" for clarity)

4. Complete playoff simulation:
   - Simulate Wild Card → Divisional schedules automatically
   - Simulate Divisional → Conference schedules automatically
   - Simulate Conference → Super Bowl schedules automatically
   - Simulate Super Bowl → Playoffs complete!

#### Option 2: Use a Different Database
If you want to keep the old data for reference:

1. Run with a custom database:
   ```python
   simulator = InteractivePlayoffSimulator(
       dynasty_id="my_new_dynasty",
       database_path="demo/interactive_playoff_sim/data/playoffs_2024_new.db"
   )
   ```

2. Or rename the old database:
   ```bash
   mv demo/interactive_playoff_sim/data/playoffs_2024.db \
      demo/interactive_playoff_sim/data/playoffs_2024_old.db
   ```

### Test Results

All diagnostic tests pass successfully:

```
✅ Dynasty with 'playoff_' prefix: 4 Divisional games simulated
✅ Dynasty without 'playoff_' prefix: 4 Divisional games simulated
✅ Event retrieval with double prefix: 4 Divisional games simulated
```

### How to Verify It's Working

After starting a new dynasty, you should see:

1. **Wild Card Round**:
   - 6 games simulate
   - Status shows: "Divisional Round has been SCHEDULED"
   - Message: "But NOT YET SIMULATED!"

2. **Select option [3] again to simulate Divisional**:
   - Calendar advances 6-7 days (to Jan 18-19)
   - 4 Divisional games simulate
   - Status shows: "Conference Round has been SCHEDULED"

3. **Continue through Conference and Super Bowl**:
   - Each round schedules the next automatically
   - All 13 playoff games complete (6+4+2+1)

### Fixes Applied

The following bugs were fixed in this session:

1. **Round scheduling logic** - Now correctly detects completed round before scheduling next
2. **Game ID parsing** - Regex handles dynasty IDs with underscores
3. **Round completion checking** - Checks specific round, not active round during loop
4. **Advance week error** - Correctly handles round completion data structures
5. **Status display** - Shows active round based on completion, not simulation state

### If Problem Persists

If you still experience issues after deleting the database:

1. Check you're running from the correct directory:
   ```bash
   pwd  # Should show: .../the-owners-sim
   ```

2. Verify Python path:
   ```bash
   export PYTHONPATH=src
   python demo/interactive_playoff_sim/interactive_playoff_sim.py
   ```

3. Run diagnostic tests:
   ```bash
   python demo/interactive_playoff_sim/test_complete_workflow.py
   python demo/interactive_playoff_sim/test_dynasty_id_issue.py
   ```

4. Check the logs - if errors appear, they'll show what's failing

### Summary

**Problem**: Old dynasty data from before fixes
**Solution**: Delete database and start new dynasty
**Expected**: Full playoff progression works perfectly (6→4→2→1 games)
