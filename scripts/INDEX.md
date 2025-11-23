# Playoff Winners Backfill - Resource Index

## Quick Navigation

### I want to...

**Run the script immediately**
→ See: [QUICK_START.md](QUICK_START.md)

**Learn step-by-step how to use it**
→ See: [USAGE_WALKTHROUGH.md](USAGE_WALKTHROUGH.md)

**Get complete technical details**
→ See: [BACKFILL_WINNERS_README.md](BACKFILL_WINNERS_README.md)

**Understand what was done**
→ See: [../BACKFILL_WINNERS_SUMMARY.md](../BACKFILL_WINNERS_SUMMARY.md)

**Get help with the script**
→ Run: `python scripts/backfill_playoff_winners.py --help`

---

## Files Overview

### Main Executable
**`backfill_playoff_winners.py`**
- The actual script that does the work
- Executable with Python 3.13.5+
- ~12 KB, fully commented
- Handles dry-run and execute modes
- Includes comprehensive error handling

### Documentation Files

**`QUICK_START.md`** (3.8 KB)
- **Best for**: Getting started quickly
- **Contains**: TL;DR, basic commands, common scenarios
- **Read time**: 5 minutes
- **When to use**: You just want to run the script

**`USAGE_WALKTHROUGH.md`** (10 KB)
- **Best for**: Understanding how to use the script
- **Contains**: Step-by-step scenarios, verification commands, troubleshooting
- **Read time**: 15 minutes
- **When to use**: You want to understand all the ways to use it

**`BACKFILL_WINNERS_README.md`** (9 KB)
- **Best for**: Complete technical reference
- **Contains**: All options, workflows, error handling, advanced usage
- **Read time**: 20 minutes
- **When to use**: You need complete documentation

**`../BACKFILL_WINNERS_SUMMARY.md`** (8 KB)
- **Best for**: Project overview
- **Contains**: What was done, results, technical details
- **Read time**: 10 minutes
- **When to use**: You want to understand the project

**`INDEX.md`** (this file)
- Navigation guide to all resources
- Quick reference for finding what you need

---

## Command Reference

### Basic Commands

```bash
# Preview (safe - no changes)
python scripts/backfill_playoff_winners.py

# Execute (update database)
python scripts/backfill_playoff_winners.py --execute

# Help
python scripts/backfill_playoff_winners.py --help
```

### Options

```bash
--execute              # Actually update the database (default: dry-run)
--dynasty DYNASTY      # Dynasty ID (default: test1)
--season SEASON        # Season year (default: 2025)
--database PATH        # Database path (default: data/database/nfl_simulation.db)
```

### Examples

```bash
# Default dynasty (test1) and season (2025)
python scripts/backfill_playoff_winners.py --execute

# Custom dynasty
python scripts/backfill_playoff_winners.py --execute --dynasty my_dynasty

# Custom season
python scripts/backfill_playoff_winners.py --execute --season 2026

# Custom database
python scripts/backfill_playoff_winners.py --execute --database /path/to/db.db
```

---

## Three-Step Usage

### 1. Preview
```bash
python scripts/backfill_playoff_winners.py
```
Shows all games that would be updated. No database changes.

### 2. Verify
Review the output to ensure all games and winners are correct.

### 3. Execute
```bash
python scripts/backfill_playoff_winners.py --execute
```
Updates the database with winner information.

---

## Verification Commands

### Check if backfill was successful
```bash
sqlite3 data/database/nfl_simulation.db << 'EOF'
SELECT COUNT(*) FROM events
WHERE dynasty_id='test1'
  AND json_extract(data, '$.parameters.season_type')='playoffs'
  AND json_extract(data, '$.results.winner_id') IS NOT NULL;
EOF
# Output should be: 13
```

### View all winners
```bash
sqlite3 data/database/nfl_simulation.db << 'EOF'
SELECT
  json_extract(data, '$.parameters.game_type') as round,
  json_extract(data, '$.results.winner_name') as winner,
  json_extract(data, '$.results.away_score') || '-' ||
  json_extract(data, '$.results.home_score') as score
FROM events
WHERE dynasty_id='test1'
  AND event_type='GAME'
  AND json_extract(data, '$.parameters.season')=2025
  AND json_extract(data, '$.parameters.season_type')='playoffs'
ORDER BY json_extract(data, '$.parameters.game_type');
EOF
```

---

## Troubleshooting

### "Database not found"
→ See: [USAGE_WALKTHROUGH.md - Troubleshooting](USAGE_WALKTHROUGH.md#troubleshooting)

### "Found 0 playoff games"
→ See: [USAGE_WALKTHROUGH.md - Problem: Found 0 playoff games](USAGE_WALKTHROUGH.md#problem-found-0-playoff-games)

### "Update didn't apply"
→ See: [USAGE_WALKTHROUGH.md - Problem: Update didn't apply](USAGE_WALKTHROUGH.md#problem-update-didnt-apply)

### Other issues
→ See: [BACKFILL_WINNERS_README.md - Troubleshooting](BACKFILL_WINNERS_README.md#troubleshooting)

---

## Key Information

### What It Does
Backfills missing `winner_id` and `winner_name` for 13 playoff games in dynasty 'test1' (season 2025).

### How Long It Takes
- Dry-run: < 1 second
- Execute: < 1 second
- Processing 13 games: < 1 second

### Data Affected
- Database: `data/database/nfl_simulation.db`
- Table: `events`
- Records: 13 (playoff games only)
- Dynasty: test1 (default)
- Season: 2025 (default)

### Safety Features
- Dry-run mode (default)
- Transactional updates (all-or-nothing)
- Error handling and logging
- Idempotent (safe to run multiple times)

### Success Rate
- Games backfilled: 13/13 (100%)
- Errors: 0
- Data integrity: verified

---

## Documentation Structure

```
/scripts/
├── backfill_playoff_winners.py      [MAIN SCRIPT]
├── INDEX.md                         [THIS FILE]
├── QUICK_START.md                   [QUICK REFERENCE]
├── USAGE_WALKTHROUGH.md             [STEP-BY-STEP GUIDE]
└── BACKFILL_WINNERS_README.md       [COMPLETE REFERENCE]

/
└── BACKFILL_WINNERS_SUMMARY.md      [PROJECT OVERVIEW]
```

---

## Getting Help

### For Quick Reference
```bash
python scripts/backfill_playoff_winners.py --help
```

### For Usage Examples
See: [USAGE_WALKTHROUGH.md](USAGE_WALKTHROUGH.md)

### For Complete Details
See: [BACKFILL_WINNERS_README.md](BACKFILL_WINNERS_README.md)

### For Project Overview
See: [../BACKFILL_WINNERS_SUMMARY.md](../BACKFILL_WINNERS_SUMMARY.md)

---

## Quick Links

| Resource | Purpose | Read Time |
|----------|---------|-----------|
| [QUICK_START.md](QUICK_START.md) | Get started quickly | 5 min |
| [USAGE_WALKTHROUGH.md](USAGE_WALKTHROUGH.md) | Learn all usage patterns | 15 min |
| [BACKFILL_WINNERS_README.md](BACKFILL_WINNERS_README.md) | Complete reference | 20 min |
| [../BACKFILL_WINNERS_SUMMARY.md](../BACKFILL_WINNERS_SUMMARY.md) | Project overview | 10 min |

---

## Summary

**Script**: Ready to use
**Documentation**: Complete
**Status**: Production-ready
**All 13 games**: Successfully backfilled and verified

Start with [QUICK_START.md](QUICK_START.md) for the fastest path to running the script.

---

**Questions?** See the relevant documentation file above, or run:
```bash
python scripts/backfill_playoff_winners.py --help
```
