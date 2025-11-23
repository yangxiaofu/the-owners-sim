# Quick Start: Playoff Winners Backfill

## TL;DR

```bash
# 1. Preview what will be updated (safe, no changes)
python scripts/backfill_playoff_winners.py

# 2. If it looks correct, apply the updates
python scripts/backfill_playoff_winners.py --execute

# 3. Done! All 13 playoff games now have winner data
```

## What This Script Does

Fixes missing `winner_id` and `winner_name` for all 13 playoff games in dynasty 'test1' (season 2025).

**Before**: `winner_id: NULL`, `winner_name: NULL`
**After**: `winner_id: 2`, `winner_name: "Miami Dolphins"` (example)

## Why You Need It

Draft order calculation requires knowing which team won each playoff game. Missing winner data blocks this calculation.

## How to Use

### Option 1: Default Settings (Recommended)

```bash
# Preview (safe - no database changes)
python scripts/backfill_playoff_winners.py

# Execute (applies updates)
python scripts/backfill_playoff_winners.py --execute
```

### Option 2: Custom Dynasty/Season

```bash
# Different dynasty
python scripts/backfill_playoff_winners.py --execute --dynasty my_dynasty

# Different season
python scripts/backfill_playoff_winners.py --execute --season 2026

# Both
python scripts/backfill_playoff_winners.py --execute --dynasty my_dynasty --season 2026
```

### Option 3: Custom Database Path

```bash
python scripts/backfill_playoff_winners.py --execute --database /path/to/db.db
```

## Output Example

```
================================================================================
PLAYOFF WINNERS BACKFILL - DRY RUN
================================================================================

Found 13 playoff game(s) with missing winner data

1. WILD_CARD
   Indianapolis Colts (10) 11
   Pittsburgh Steelers (8) 27
   → Winner: Pittsburgh Steelers (ID: 8)

2. WILD_CARD
   Las Vegas Raiders (15) 19
   Los Angeles Chargers (16) 10
   → Winner: Las Vegas Raiders (ID: 15)

... [shows all 13 games] ...

[DRY RUN MODE] No changes made to database
Run with --execute flag to apply updates
```

## Key Features

- **Safe Dry-Run**: Preview all changes before applying
- **Transaction Safety**: All-or-nothing database updates
- **Error Logging**: Reports any problems encountered
- **Idempotent**: Safe to run multiple times
- **Fast**: Processes 13 games in < 1 second

## Verification

After execution, verify with:

```bash
sqlite3 data/database/nfl_simulation.db << 'EOF'
SELECT COUNT(*) as games_with_winners
FROM events
WHERE dynasty_id = 'test1'
  AND event_type = 'GAME'
  AND json_extract(data, '$.parameters.season') = 2025
  AND json_extract(data, '$.parameters.season_type') = 'playoffs'
  AND json_extract(data, '$.results.winner_id') IS NOT NULL;
EOF

# Should return: 13
```

## Common Scenarios

### I want to see what will change first
```bash
python scripts/backfill_playoff_winners.py
# Shows 13 games without applying changes
```

### All looks good, apply the updates
```bash
python scripts/backfill_playoff_winners.py --execute
# Updates database, shows confirmation
```

### I want to process a different dynasty
```bash
python scripts/backfill_playoff_winners.py --execute --dynasty custom_name
```

### I made a mistake, can I undo it?
The script doesn't store backups, but you can restore from your git backup or database backup if you have one.

For future safeguards, always run the dry-run mode first!

## Database Changes Made

Each event record's JSON data is updated:

```json
{
  "results": {
    "away_score": 11,
    "home_score": 27,
    "winner_id": 8,              ← ADDED
    "winner_name": "Pittsburgh Steelers"  ← ADDED
  }
}
```

## Requirements

- Python 3.13.5+
- Database: `data/database/nfl_simulation.db`
- Team data: `src/data/teams.json`

## For More Details

See: `scripts/BACKFILL_WINNERS_README.md`

---

**Status**: Script successfully backfilled all 13 playoff games for dynasty 'test1' (season 2025)
