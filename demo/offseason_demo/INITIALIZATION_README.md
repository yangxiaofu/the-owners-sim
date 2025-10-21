# Demo Initialization Script

Automated initialization script for the offseason UI demo database.

## Quick Start

```bash
# From project root
python demo/offseason_demo/initialize_demo.py

# Reset and recreate database
python demo/offseason_demo/initialize_demo.py --reset
```

## What It Does

The initialization script automates the complete setup of the offseason demo database:

1. **Database Check**: Verifies if `offseason_demo.db` exists
2. **Schema Validation**: Checks for required tables (players, contracts, events, etc.)
3. **Data Validation**: Verifies expected record counts
4. **Mock Data Generation**: Creates realistic NFL data if database is missing/invalid
5. **Event Scheduling**: Schedules 14 offseason events from Feb 9 → Sept 5, 2025

## Features

### Automatic Detection

The script automatically detects if a valid database already exists:

```bash
$ python demo/offseason_demo/initialize_demo.py

================================================================================
OFFSEASON DEMO INITIALIZATION
================================================================================

✓ Database already exists and is valid
  Path: /Users/.../data/database/offseason_demo.db

  Players: 542
  Contracts: 542
  Salary Cap Records: 32
  Events: 14

✓ Demo database is ready to use
  Run with --reset to recreate database
```

### Force Reset

Use `--reset` to delete and recreate the database:

```bash
$ python demo/offseason_demo/initialize_demo.py --reset

⚠️  Reset requested - deleting existing database
✓ Deleted existing database: offseason_demo.db

📦 Creating new demo database...
```

### Custom Configuration

Customize database path, dynasty ID, and season year:

```bash
# Custom database location
python demo/offseason_demo/initialize_demo.py --database custom_demo.db

# Custom dynasty ID
python demo/offseason_demo/initialize_demo.py --dynasty "my_custom_dynasty"

# Custom season year
python demo/offseason_demo/initialize_demo.py --season 2025
```

## Generated Data

### Players (540-550 total)

- **32 NFL Teams**: All current NFL teams with realistic rosters
- **Position Distribution**: QB (64), RB (96), WR (128), TE (64), OL (128), DL (32), LB (32), DB (32)
- **Realistic Attributes**: Overall ratings, age, experience, position-specific attributes
- **Dynasty Isolation**: All players tagged with `dynasty_id="ui_offseason_demo"`

### Contracts (540-550 total)

- **Realistic Salaries**: Position-based salary ranges (QB: $1M-$50M, RB: $800K-$15M, etc.)
- **Contract Years**: Random contract lengths (1-5 years)
- **Contract Types**: Standard player contracts
- **Cap Hits**: Realistic cap hit calculations

### Salary Cap Records (32)

- **Per-Team Tracking**: One record per NFL team
- **2025 Season Cap**: $255.4M per team
- **Usage Percentages**: Teams use 85-95% of available cap
- **Remaining Cap Space**: Realistic amounts for offseason transactions

### Offseason Events (14)

1. **Super Bowl** (Feb 9, 2025) - Milestone
2. **NFL Combine** (March 1, 2025) - Milestone
3. **Franchise Tag Deadline** (March 5, 2025) - Deadline
4. **Legal Tampering Period** (March 11-13, 2025) - Window (START + END)
5. **Free Agency Opens** (March 13, 2025) - Deadline
6. **Free Agency Window** (March 13 - Sept 5, 2025) - Window (START + END)
7. **Draft Start** (April 24, 2025) - Deadline
8. **Draft End** (April 27, 2025) - Deadline
9. **OTAs Begin** (May 20, 2025) - Milestone
10. **Training Camp** (July 23, 2025) - Milestone
11. **Roster Cuts** (August 26, 2025) - Deadline
12. **Season Begins** (Sept 5, 2025) - Milestone

## Database Validation

The script validates both schema and data:

### Schema Validation

Required tables:
- `players` - Player roster data
- `player_contracts` - Contract details
- `team_salary_cap` - Salary cap tracking
- `events` - Offseason event schedule
- `team_rosters` - Team roster assignments

### Data Count Validation

Expected minimums:
- **Players**: ≥500 (actual: 540-550)
- **Contracts**: ≥500 (actual: 540-550)
- **Salary Cap Records**: =32 (one per team)
- **Events**: ≥10 (actual: 14)

## Usage in Code

You can also use the initializer programmatically:

```python
from initialize_demo import DemoInitializer

# Create initializer
initializer = DemoInitializer(
    database_path="data/database/offseason_demo.db",
    dynasty_id="ui_offseason_demo",
    season_year=2024
)

# Initialize (creates if missing, validates if exists)
db_path = initializer.initialize()

# Force reset
db_path = initializer.initialize(force_reset=True)

# Check validation only
if initializer.is_database_valid():
    print("Database is ready!")
```

## Troubleshooting

### Database Already Exists But Is Invalid

If the database exists but validation fails:

```bash
# Delete and recreate
python demo/offseason_demo/initialize_demo.py --reset
```

### Missing Python Modules

Ensure you're running from the project root and all dependencies are installed:

```bash
# Check Python environment
python --version  # Should be 3.13.5+

# The script auto-configures PYTHONPATH - no manual setup needed
```

### Database Creation Fails

If database creation fails with permission errors:

```bash
# Ensure data/database directory exists and is writable
mkdir -p data/database
chmod 755 data/database
```

## Integration with Main Demo

This script is called automatically by `main_offseason_demo.py` on first run:

```python
from initialize_demo import DemoInitializer

# Initialize database before launching UI
initializer = DemoInitializer()
db_path = initializer.initialize()

# Launch UI with initialized database
app = QApplication(sys.argv)
window = MainWindow(database_path=db_path, dynasty_id="ui_offseason_demo")
window.show()
```

## CLI Reference

```
usage: initialize_demo.py [-h] [--database DATABASE] [--dynasty DYNASTY]
                          [--season SEASON] [--reset]

Initialize offseason demo database

optional arguments:
  -h, --help           show this help message and exit
  --database DATABASE  Path to demo database file (default: data/database/offseason_demo.db)
  --dynasty DYNASTY    Dynasty ID for data isolation (default: ui_offseason_demo)
  --season SEASON      NFL season year (default: 2024)
  --reset              Delete and recreate database
```

## Related Files

- **`mock_data_generator.py`**: Generates realistic NFL player and contract data
- **`event_scheduler.py`**: Schedules 14 offseason events with proper types
- **`demo_domain_models.py`**: Domain models for UI data access
- **`placeholder_handlers.py`**: PySide6 modal dialogs for event simulation

## Next Steps

After running the initialization script:

1. Verify database was created: `ls -lh data/database/offseason_demo.db`
2. Inspect database contents: `sqlite3 data/database/offseason_demo.db`
3. Run the main UI demo: `python demo/offseason_demo/main_offseason_demo.py` (coming soon)

## Development Notes

- **Dynasty Isolation**: All data uses `dynasty_id="ui_offseason_demo"` for isolation
- **Deterministic Generation**: Uses seeded random for reproducible results
- **No External Dependencies**: Only uses Python standard library + existing src modules
- **Idempotent**: Safe to run multiple times - won't duplicate data
