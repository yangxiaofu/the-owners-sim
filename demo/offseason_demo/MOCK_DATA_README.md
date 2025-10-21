# Offseason UI Mock Data Generator

Mock data generator for testing the Offseason UI without requiring a full season simulation.

## Overview

This module generates realistic fixture data for all 32 NFL teams including:
- **Players**: 5-10 players per team (547 total) with position-based distribution
- **Contracts**: Realistic contract data with position-appropriate salaries
- **Salary Cap**: Team salary cap data with ~85-95% cap usage per team

All data is **deterministic** - running the generator multiple times produces the same data for consistent testing.

## Quick Start

```bash
# Generate mock data (from project root)
PYTHONPATH=src python demo/offseason_demo/mock_data_generator.py
```

This creates:
- Database: `demo/offseason_demo/offseason_demo.db`
- Dynasty: `ui_offseason_demo`
- Season: 2025

## Generated Data Details

### Players (547 total)

Position distribution:
- **QB**: 79 players (~2-3 per team)
- **RB**: 80 players (~2-3 per team)
- **WR**: 79 players (~2-3 per team)
- **TE**: 46 players (~1-2 per team)
- **OL**: 47 players (~1-2 per team)
- **DL**: 49 players (~1-2 per team)
- **LB**: 56 players (~1-2 per team)
- **DB**: 47 players (~1-2 per team)
- **K**: 32 players (1 per team)
- **P**: 32 players (1 per team)

Player naming: `{TeamName} {Position}{Index}`
- Example: `Bills QB1`, `Cowboys WR2`, `Lions RB1`

### Contracts (547 total)

Salary ranges by position:
- **QB**: $1M - $50M (avg: $25M)
- **WR**: $900K - $25M (avg: $10M)
- **DL**: $900K - $22M (avg: $9M)
- **OL**: $850K - $20M (avg: $8M)
- **DB**: $900K - $20M (avg: $8M)
- **LB**: $850K - $18M (avg: $7M)
- **TE**: $800K - $18M (avg: $6M)
- **RB**: $800K - $15M (avg: $5M)
- **K**: $1M - $6M (avg: $2.5M)
- **P**: $900K - $4M (avg: $1.8M)

Contract features:
- **Years**: 1-6 years based on position and salary
- **Signing bonus**: 10-30% of total value
- **Guaranteed money**: 30-60% of total value
- **Contract type**: All VETERAN contracts
- **Start year**: 2025

### Salary Cap (32 teams)

- **Salary cap**: $255,400,000 (2024 NFL cap)
- **Usage**: 85-95% per team (realistic variance)
- **Carryover**: Random -$5M to +$10M
- **Dead money**: Random $0 to $15M
- **LTBE incentives**: Random $0 to $5M
- **Top-51 active**: TRUE (offseason mode)

Example cap data:
```
Team 1 (Buffalo Bills):     $236.9M used (92.8%)
Team 2 (Miami Dolphins):    $228.5M used (89.5%)
Team 3 (New England):       $233.4M used (91.4%)
```

## Database Schema

The generator creates/uses the following tables:

### Core Tables (from DatabaseConnection)
- `dynasties` - Dynasty metadata
- `players` - Player roster data
- `player_contracts` - Contract details
- `contract_year_details` - Year-by-year contract breakdown

### Additional Tables
- `team_salary_cap` - Team cap data (created by generator if missing)

## Using with UI

The generated database can be used with the Offseason UI:

```python
from ui.main_window import OffseasonMainWindow
from database.api import DatabaseAPI

# Load data
db_api = DatabaseAPI("demo/offseason_demo/offseason_demo.db")
window = OffseasonMainWindow(dynasty_id="ui_offseason_demo", db_api=db_api)
window.show()
```

## Customization

You can customize the data generation by modifying parameters:

```python
from demo.offseason_demo.mock_data_generator import generate_mock_data

# Custom dynasty and season
counts = generate_mock_data(
    database_path="my_custom.db",
    dynasty_id="my_test_dynasty",
    current_season=2026
)
```

### Position Configuration

Modify `POSITION_CONFIG` in `mock_data_generator.py` to adjust:
- Player counts per position
- Salary ranges
- Average salaries

## Data Verification

Verify the generated data:

```bash
# Check player count
sqlite3 demo/offseason_demo/offseason_demo.db \
  "SELECT COUNT(*) FROM players WHERE dynasty_id='ui_offseason_demo'"

# Check cap usage by team
sqlite3 demo/offseason_demo/offseason_demo.db \
  "SELECT team_id, active_contracts_total, salary_cap_limit
   FROM team_salary_cap WHERE dynasty_id='ui_offseason_demo'"

# Check position distribution
sqlite3 demo/offseason_demo/offseason_demo.db \
  "SELECT positions, COUNT(*) FROM players
   WHERE dynasty_id='ui_offseason_demo' GROUP BY positions"
```

## Implementation Details

### Deterministic Generation

The generator uses seeded random number generation to ensure consistent data:

```python
# Player salaries based on team_id + player_id
seed = team_id * 10000 + player_id
salary = generate_salary(position, seed)

# Team-specific randomness
random.seed(team_id * 1000)
usage_pct = random.uniform(0.85, 0.95)
```

### Realistic Distributions

- **Salaries**: Weighted 60% towards average, 40% extremes
- **Cap usage**: 85-95% to simulate offseason cap management
- **Player counts**: Varied by position importance (QB/RB/WR: 2-3, K/P: 1)

### Database Integration

The generator:
1. Initializes database schema via `DatabaseConnection`
2. Creates dynasty record if missing
3. Generates all teams in parallel
4. Batch inserts for performance
5. Uses transactions for data integrity

## Notes

- **Dynasty ID**: All data uses `dynasty_id='ui_offseason_demo'`
- **Season**: Default is 2025
- **Consistency**: Running generator multiple times overwrites with same data
- **Performance**: Generates 500+ records in < 1 second
- **Isolation**: Data is completely isolated by dynasty_id

## Future Enhancements

Potential additions:
- [ ] Draft pick generation
- [ ] Free agent market (0 team_id)
- [ ] Player ratings and attributes
- [ ] Injury status
- [ ] Contract escalators and options
- [ ] Franchise tag data
- [ ] Dead money history
