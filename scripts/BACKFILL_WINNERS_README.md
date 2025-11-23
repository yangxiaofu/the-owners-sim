# Backfill Playoff Winners Script

## Overview

This script backfills missing `winner_id` and `winner_name` data for playoff games in the database.

**Problem**: All 13 playoff games in dynasty 'test1' (season 2025) have complete score data but null `winner_id`/`winner_name` in the events table, which blocks draft order calculation.

**Solution**: Calculates the winner from the game scores and updates the event data in the database.

## Location

```
scripts/backfill_playoff_winners.py
```

## Usage

### Dry-Run Mode (Default - Safe Preview)

```bash
python scripts/backfill_playoff_winners.py
```

This shows exactly what will be updated without modifying the database.

**Output Example**:
```
================================================================================
PLAYOFF WINNERS BACKFILL - DRY RUN
================================================================================
Database: data/database/nfl_simulation.db
Dynasty: test1
Season: 2025

Found 13 playoff game(s) with missing winner data

1. WILD_CARD
   Indianapolis Colts (10) 11
   Pittsburgh Steelers (8) 27
   → Winner: Pittsburgh Steelers (ID: 8)

2. WILD_CARD
   Las Vegas Raiders (15) 19
   Los Angeles Chargers (16) 10
   → Winner: Las Vegas Raiders (ID: 15)

... [11 more games] ...

13. SUPER_BOWL
   Miami Dolphins (2) 23
   Chicago Bears (21) 21
   → Winner: Miami Dolphins (ID: 2)

================================================================================
SUMMARY
================================================================================
Games processed: 13

[DRY RUN MODE] No changes made to database
Run with --execute flag to apply updates
================================================================================
```

### Execute Mode (Apply Updates)

```bash
python scripts/backfill_playoff_winners.py --execute
```

This actually updates the database with the calculated winners.

**Output**: Same as dry-run but with the addition of:
```
✓ Successfully updated 13 game(s) in database

[EXECUTE MODE] All updates applied
```

## Command-Line Options

### `--execute`
**Type**: Boolean flag
**Default**: False (dry-run mode)
**Description**: Activates execute mode to actually update the database. Without this flag, the script only shows what would be updated.

```bash
python scripts/backfill_playoff_winners.py --execute
```

### `--dynasty`
**Type**: String
**Default**: `test1`
**Description**: Dynasty ID to process

```bash
python scripts/backfill_playoff_winners.py --execute --dynasty custom_dynasty
```

### `--season`
**Type**: Integer
**Default**: `2025`
**Description**: Season year to process

```bash
python scripts/backfill_playoff_winners.py --execute --season 2026
```

### `--database`
**Type**: String
**Default**: `data/database/nfl_simulation.db`
**Description**: Path to the SQLite database file

```bash
python scripts/backfill_playoff_winners.py --execute --database /custom/path/db.db
```

## How It Works

### 1. Query Phase
- Queries the `events` table for games matching:
  - Dynasty ID (default: 'test1')
  - Season year (default: 2025)
  - Season type: 'playoffs'
  - Event type: 'GAME'
  - Missing `winner_id` (null in event data)

### 2. Processing Phase
For each game found:
- Extracts:
  - `away_team_id` and `home_team_id` from parameters
  - `away_score` and `home_score` from results
- Calculates winner:
  - Team with higher score wins
  - Ties (shouldn't happen in playoffs) are logged as errors
- Looks up team name using `TeamDataLoader`
- Displays before/after state

### 3. Update Phase (Execute Mode Only)
- Updates each event's JSON data with:
  - `results.winner_id`: Integer ID of winning team
  - `results.winner_name`: String name of winning team
- Uses database transaction for safety (all or nothing)
- Verifies update success

## Event Data Structure

The script works with this event data structure:

```json
{
  "event_id": "game_20250115_10_at_8",
  "event_type": "GAME",
  "dynasty_id": "test1",
  "data": {
    "parameters": {
      "away_team_id": 10,
      "home_team_id": 8,
      "season": 2025,
      "season_type": "playoffs",
      "game_type": "wild_card"
    },
    "results": {
      "away_score": 11,
      "home_score": 27,
      "winner_id": 8,        ← BACKFILLED
      "winner_name": "Pittsburgh Steelers"  ← BACKFILLED
    }
  }
}
```

## Error Handling

The script logs errors for:
- Invalid JSON in event data
- Missing team IDs in game data
- Missing score data
- Tie scores (shouldn't occur in playoffs)
- Team lookup failures (uses fallback "Team {ID}" format)

All errors are displayed in the summary section:

```
Errors encountered: 1
  - Event xyz123: Missing team IDs
```

Errors do not prevent other games from being processed.

## Example Workflow

### 1. First, Preview the Changes (Safe)
```bash
$ python scripts/backfill_playoff_winners.py

Found 13 playoff game(s) with missing winner data
[Shows all 13 games to be updated]
[DRY RUN MODE] No changes made to database
Run with --execute flag to apply updates
```

### 2. Verify the Games Look Correct
Review the output to ensure:
- Correct game types (wild_card, divisional, conference, super_bowl)
- Correct teams and scores
- Correct winners (higher score wins)

### 3. Execute the Updates (If Satisfied)
```bash
$ python scripts/backfill_playoff_winners.py --execute

Found 13 playoff game(s) with missing winner data
[Shows all 13 games being updated]
✓ Successfully updated 13 game(s) in database
[EXECUTE MODE] All updates applied
```

### 4. Verify in Database
```bash
sqlite3 data/database/nfl_simulation.db \
  "SELECT COUNT(*) FROM events WHERE \
   dynasty_id='test1' AND json_extract(data, '$.parameters.season_type')='playoffs' \
   AND json_extract(data, '$.results.winner_id') IS NOT NULL"

# Should return: 13
```

## Database Changes

After running with `--execute`, the events table changes:

**Before**:
```
winner_id: NULL
winner_name: NULL
```

**After**:
```
winner_id: 8
winner_name: "Pittsburgh Steelers"
```

### Transaction Safety
- All updates happen in a single transaction
- If any update fails, entire transaction is rolled back
- No partial updates to the database

## Testing

To test with custom data:

```bash
# Test with different dynasty
python scripts/backfill_playoff_winners.py --dynasty my_dynasty

# Test with different season
python scripts/backfill_playoff_winners.py --season 2026

# Test with both
python scripts/backfill_playoff_winners.py --execute --dynasty custom --season 2026
```

## Requirements

- Python 3.13.5+
- SQLite3
- Database: `data/database/nfl_simulation.db` (or custom path)
- Team data: `src/data/teams.json`

## Exit Codes

- `0`: Success (no errors, or no updates needed)
- `1`: One or more errors occurred during processing

## Performance

- Typical execution time for 13 games: < 1 second
- Database I/O operations are optimized with indexes
- JSON parsing done in Python (SQLite JSON functions for queries)

## Troubleshooting

### "Database not found at ..."
The script can't find the database file. Check:
- File exists at path
- Path is correct relative to where you're running the script from
- Use absolute path or `--database` flag if needed

### "Invalid JSON for event ..."
Event data in database is corrupted. Check:
- Run with `--execute` to fix just the affected game
- May indicate database corruption

### No games found
- Check dynasty ID is correct (`--dynasty test1`)
- Check season is correct (`--season 2025`)
- Check games are actually in the database with null winner_id

### Wrong team names
- Check `src/data/teams.json` has all 32 NFL teams defined
- TeamDataLoader should have all teams, or falls back to "Team {ID}" format

## Advanced Usage

### Process Multiple Dynasties

```bash
# Test all dynasties in dry-run
for dynasty in dynasty1 dynasty2 dynasty3; do
  python scripts/backfill_playoff_winners.py --dynasty $dynasty
done

# Then execute for each
for dynasty in dynasty1 dynasty2 dynasty3; do
  python scripts/backfill_playoff_winners.py --execute --dynasty $dynasty
done
```

### Generate SQL Report

```bash
# See all playoffs with winners
sqlite3 data/database/nfl_simulation.db << 'EOF'
SELECT
  json_extract(data, '$.parameters.game_type') as game_type,
  json_extract(data, '$.results.winner_name') as winner,
  json_extract(data, '$.results.away_score') || '-' || json_extract(data, '$.results.home_score') as score
FROM events
WHERE dynasty_id = 'test1'
  AND event_type = 'GAME'
  AND json_extract(data, '$.parameters.season') = 2025
  AND json_extract(data, '$.parameters.season_type') = 'playoffs'
ORDER BY json_extract(data, '$.parameters.game_type'), json_extract(data, '$.parameters.game_date');
EOF
```

## Notes

- Script is idempotent: running it multiple times with `--execute` is safe
- All-or-nothing updates: transaction rolls back if any game fails
- Dry-run has zero side effects: safe to run as many times as needed
- Team names are case-sensitive (matches NFL official names from `teams.json`)

## Future Enhancements

Potential improvements:
- Support for non-playoff games (regular season, preseason)
- Batch processing multiple dynasties/seasons
- CSV export of results
- Conflict resolution for games with existing winner_id
- Audit trail of changes made
