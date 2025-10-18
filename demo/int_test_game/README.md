# INT Test Demo

Quick single-game simulation to test QB interception tracking.

## Purpose

This demo tests whether QB interceptions are being correctly saved to the database. It uses **the exact same workflow code** as the production season simulation, so any issues found here will also affect the main application.

## What It Tests

1. **Play Simulation**: QB throws interception → `interceptions_thrown` attribute set
2. **Stats Accumulation**: `interceptions_thrown` accumulated across plays
3. **Database Persistence**: `interceptions_thrown` saved to `passing_interceptions` column
4. **Data Verification**: Query database to confirm INTs were saved

## Quick Start

```bash
# Run from project root
PYTHONPATH=src python demo/int_test_game/int_test_demo.py
```

## Expected Output

### Debug Messages

Watch for these 🔴 INT DEBUG messages during simulation:

1. **Play Simulation**: `Set QB [name] interceptions_thrown=1`
2. **Stats Accumulation**: `[name] has interceptions_thrown=X`
3. **Persistence**: `[name] has interceptions_thrown=X` (when saving)

If you see **"BLOCKED!"** message, it means `get_total_stats()` returned empty and stats are being dropped!

### Database Verification

The demo automatically queries the database after simulation and shows:

```
📊 Summary:
  Total Games                   : 1
  QB INTs (passing_interceptions): X  ← Should be > 0!
  DB INTs (interceptions)       : Y  ← Defensive INTs (may be 0)
```

### Test Results

- ✅ **PASS**: `QB INTs > 0` means INT tracking is working
- ❌ **FAIL**: `QB INTs = 0` means INT tracking is still broken

## Database Structure

The test uses two separate columns for interceptions:

| Column | Purpose | Source Attribute |
|--------|---------|-----------------|
| `passing_interceptions` | QB interceptions thrown | `interceptions_thrown` |
| `interceptions` | Defensive interceptions caught | `interceptions` |

## Manual Verification

If you want to check the database yourself:

```bash
# Open database
sqlite3 demo/int_test_game/data/int_test.db

# Query QB stats
SELECT player_name, passing_attempts, passing_interceptions, interceptions
FROM player_game_stats
WHERE dynasty_id='int_test' AND passing_attempts > 0;

# Query DB stats
SELECT player_name, position, interceptions
FROM player_game_stats
WHERE dynasty_id='int_test' AND interceptions > 0;
```

## Workflow Integration

This demo uses `SimulationWorkflow` from `src/workflows/simulation_workflow.py`, which is the same 3-stage workflow used in:

- Interactive season simulation
- Full season simulation
- Production UI

**If this demo fails, the production code is also broken.**

## Troubleshooting

### No INT Debug Messages

If you don't see any 🔴 INT DEBUG messages, the play engine might not be generating interceptions. Try running the demo multiple times or increasing the number of games simulated.

### "BLOCKED!" Message Appears

This means `get_total_stats()` is returning an empty dict for the QB, which prevents accumulation. The issue is likely in `src/constants/player_stats_fields.py` where `ALL_STAT_FIELDS` is defined. Check if `interceptions_thrown` is included in that set.

### Database Shows Zeros

If debug messages show INTs being set, but database has zeros, the issue is in the persistence layer (`src/persistence/daily_persister.py`). Check the INSERT statement includes `passing_interceptions` column.

## Files Created

- `int_test.db` - Test database (can be deleted between runs)
- All data isolated under dynasty_id `"int_test"`
