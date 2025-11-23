# Complete Usage Walkthrough

## Getting Started

### Step 1: Navigate to Project Root
```bash
cd /path/to/the-owners-sim
```

### Step 2: View Help (Optional)
```bash
python scripts/backfill_playoff_winners.py --help

# Output:
# usage: backfill_playoff_winners.py [-h] [--execute] [--dynasty DYNASTY]
#                                    [--season SEASON] [--database DATABASE]
#
# Backfill missing winner data for playoff games
#
# options:
#   -h, --help           show this help message and exit
#   --execute            Actually execute the updates (default: dry-run mode)
#   --dynasty DYNASTY    Dynasty ID (default: test1)
#   --season SEASON      Season year (default: 2025)
#   --database DATABASE  Path to database (default:
#                        data/database/nfl_simulation.db)
```

## Standard Workflow

### Scenario A: Process Default Dynasty (test1, 2025)

#### 1. Preview the Changes
```bash
python scripts/backfill_playoff_winners.py
```

**Output**: Shows all 13 playoff games with their scores and calculated winners
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

[DRY RUN MODE] No changes made to database
Run with --execute flag to apply updates
```

**What to do**:
- Review the scores and winners
- Ensure all teams and scores are correct
- Verify the winner calculations (higher score = winner)
- If everything looks good, proceed to step 2

#### 2. Apply the Updates
```bash
python scripts/backfill_playoff_winners.py --execute
```

**Output**: Same as dry-run but with confirmation
```
✓ Successfully updated 13 game(s) in database

[EXECUTE MODE] All updates applied
```

#### 3. Verify in Database
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

# Output should be: 13
```

---

### Scenario B: Process Different Dynasty

#### 1. Preview for Custom Dynasty
```bash
python scripts/backfill_playoff_winners.py --dynasty my_dynasty --season 2026
```

#### 2. Apply Updates
```bash
python scripts/backfill_playoff_winners.py --execute --dynasty my_dynasty --season 2026
```

#### 3. Verify
```bash
sqlite3 data/database/nfl_simulation.db << 'EOF'
SELECT COUNT(*) as games_with_winners
FROM events
WHERE dynasty_id = 'my_dynasty'
  AND event_type = 'GAME'
  AND json_extract(data, '$.parameters.season') = 2026
  AND json_extract(data, '$.parameters.season_type') = 'playoffs'
  AND json_extract(data, '$.results.winner_id') IS NOT NULL;
EOF
```

---

### Scenario C: Batch Process Multiple Dynasties

```bash
#!/bin/bash
# Process multiple dynasties

dynasties=("test1" "dynasty1" "dynasty2")
season=2025

# First, preview all changes
echo "=== PREVIEWING ALL DYNASTIES ==="
for dynasty in "${dynasties[@]}"; do
  echo ""
  echo "Dynasty: $dynasty"
  python scripts/backfill_playoff_winners.py --dynasty "$dynasty" --season "$season"
done

# Then ask for confirmation before executing
read -p "Apply all updates? (yes/no): " confirm

if [ "$confirm" = "yes" ]; then
  echo ""
  echo "=== EXECUTING ALL UPDATES ==="
  for dynasty in "${dynasties[@]}"; do
    echo ""
    echo "Updating: $dynasty"
    python scripts/backfill_playoff_winners.py --execute --dynasty "$dynasty" --season "$season"
  done
  echo ""
  echo "All updates complete!"
else
  echo "Updates cancelled."
fi
```

---

## Verification Commands

### Check Status for Specific Dynasty
```bash
# How many games have winners?
sqlite3 data/database/nfl_simulation.db << 'EOF'
SELECT
  json_extract(data, '$.parameters.season_type') as season_type,
  COUNT(*) as total_games,
  SUM(CASE WHEN json_extract(data, '$.results.winner_id') IS NOT NULL THEN 1 ELSE 0 END) as with_winners,
  SUM(CASE WHEN json_extract(data, '$.results.winner_id') IS NULL THEN 1 ELSE 0 END) as without_winners
FROM events
WHERE dynasty_id = 'test1'
  AND event_type = 'GAME'
  AND json_extract(data, '$.parameters.season') = 2025
  AND json_extract(data, '$.parameters.season_type') = 'playoffs'
GROUP BY json_extract(data, '$.parameters.season_type');
EOF
```

### View All Winners
```bash
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
ORDER BY json_extract(data, '$.parameters.game_type');
EOF
```

### Export as CSV
```bash
sqlite3 -header -csv data/database/nfl_simulation.db << 'EOF'
SELECT
  json_extract(data, '$.parameters.game_type') as round,
  json_extract(data, '$.parameters.away_team_id') as away_team_id,
  json_extract(data, '$.parameters.home_team_id') as home_team_id,
  json_extract(data, '$.results.away_score') as away_score,
  json_extract(data, '$.results.home_score') as home_score,
  json_extract(data, '$.results.winner_id') as winner_id,
  json_extract(data, '$.results.winner_name') as winner_name
FROM events
WHERE dynasty_id = 'test1'
  AND event_type = 'GAME'
  AND json_extract(data, '$.parameters.season') = 2025
  AND json_extract(data, '$.parameters.season_type') = 'playoffs'
ORDER BY json_extract(data, '$.parameters.game_type');
EOF
```

---

## Troubleshooting

### Problem: "Database not found at ..."

**Cause**: Script can't find the database file

**Solutions**:
```bash
# Option 1: Run from project root
cd /path/to/the-owners-sim
python scripts/backfill_playoff_winners.py

# Option 2: Use absolute path
python scripts/backfill_playoff_winners.py --database /absolute/path/to/db.db

# Option 3: Use relative path
python scripts/backfill_playoff_winners.py --database ../../data/database/nfl_simulation.db
```

### Problem: "Found 0 playoff game(s)"

**Cause**: Either dynasty doesn't exist, or all games already have winners

**Solutions**:
```bash
# Check dynasty ID is correct
sqlite3 data/database/nfl_simulation.db "SELECT DISTINCT dynasty_id FROM events LIMIT 10;"

# Check season is correct
sqlite3 data/database/nfl_simulation.db "SELECT DISTINCT json_extract(data, '$.parameters.season') FROM events WHERE event_type='GAME';"

# Check if games are already updated
sqlite3 data/database/nfl_simulation.db << 'EOF'
SELECT COUNT(*) FROM events
WHERE dynasty_id = 'test1'
  AND event_type = 'GAME'
  AND json_extract(data, '$.parameters.season') = 2025
  AND json_extract(data, '$.parameters.season_type') = 'playoffs'
  AND json_extract(data, '$.results.winner_id') IS NOT NULL;
EOF
```

### Problem: Update didn't apply

**Cause**: Did you forget the `--execute` flag?

**Solution**:
```bash
# Wrong (dry-run mode)
python scripts/backfill_playoff_winners.py

# Correct (execute mode)
python scripts/backfill_playoff_winners.py --execute
```

### Problem: Only some games were updated

**Cause**: Database or data corruption

**Solution**:
- Check the error messages in the output
- Examine the JSON data in affected events
- May need to manually fix corrupted records
- Contact database administrator

---

## Advanced Usage

### Automatic Backup Before Update

```bash
#!/bin/bash
# Create backup before backfill

DB_PATH="data/database/nfl_simulation.db"
BACKUP_PATH="data/database/nfl_simulation.db.backup.$(date +%Y%m%d_%H%M%S)"

echo "Creating backup: $BACKUP_PATH"
cp "$DB_PATH" "$BACKUP_PATH"

echo "Running backfill..."
python scripts/backfill_playoff_winners.py --execute

echo "Backup location: $BACKUP_PATH"
echo "If needed, restore with: cp $BACKUP_PATH $DB_PATH"
```

### Monitor Multiple Dynasties Status

```bash
#!/bin/bash
# Show which dynasties need backfill

echo "Dynasty Playoff Games Status:"
echo "=============================="
echo ""

sqlite3 data/database/nfl_simulation.db << 'EOF'
SELECT
  dynasty_id,
  COUNT(*) as total,
  SUM(CASE WHEN json_extract(data, '$.results.winner_id') IS NOT NULL THEN 1 ELSE 0 END) as with_winners,
  SUM(CASE WHEN json_extract(data, '$.results.winner_id') IS NULL THEN 1 ELSE 0 END) as without_winners
FROM events
WHERE event_type = 'GAME'
  AND json_extract(data, '$.parameters.season_type') = 'playoffs'
  AND json_extract(data, '$.results.away_score') IS NOT NULL
GROUP BY dynasty_id
ORDER BY dynasty_id;
EOF
```

### Generate Report

```bash
python3 << 'EOF'
import sqlite3
import csv

db_path = "data/database/nfl_simulation.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Query all playoff games
cursor.execute('''
  SELECT
    json_extract(data, '$.parameters.season') as season,
    json_extract(data, '$.parameters.game_type') as game_type,
    json_extract(data, '$.results.winner_name') as winner,
    json_extract(data, '$.results.away_score') as away_score,
    json_extract(data, '$.results.home_score') as home_score
  FROM events
  WHERE event_type = 'GAME'
    AND json_extract(data, '$.parameters.season_type') = 'playoffs'
    AND json_extract(data, '$.results.away_score') IS NOT NULL
  ORDER BY season, game_type
''')

# Write to CSV
with open('playoff_results.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Season', 'Round', 'Winner', 'Score'])
    for row in cursor.fetchall():
        season, game_type, winner, away_score, home_score = row
        writer.writerow([season, game_type, winner, f"{away_score}-{home_score}"])

print("Report written to: playoff_results.csv")
conn.close()
EOF
```

---

## Summary

**Three Simple Steps**:

1. **Preview**: `python scripts/backfill_playoff_winners.py`
2. **Verify**: Check the output looks correct
3. **Execute**: `python scripts/backfill_playoff_winners.py --execute`

**Always**:
- Use dry-run first
- Verify output before executing
- Keep database backups
- Check verification after execution

**For Help**:
- Full docs: `scripts/BACKFILL_WINNERS_README.md`
- Quick ref: `scripts/QUICK_START.md`
- This file: `scripts/USAGE_WALKTHROUGH.md`
