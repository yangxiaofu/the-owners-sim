# How to Configure FullGameSimulator

This guide covers the flexible configuration options available in the `FullGameSimulator` class, including persistence control, database configuration, and dynasty context management.

## Table of Contents

- [Quick Start](#quick-start)
- [Persistence Control](#persistence-control)
- [Database Configuration](#database-configuration)
- [Dynasty Context](#dynasty-context)
- [Advanced Patterns](#advanced-patterns)
- [Common Use Cases](#common-use-cases)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Basic Game Simulation

```python
from src.game_management.full_game_simulator import FullGameSimulator
from src.constants.team_ids import TeamIDs

# Simple game simulation with default settings
simulator = FullGameSimulator(
    away_team_id=TeamIDs.PHILADELPHIA_EAGLES,
    home_team_id=TeamIDs.DALLAS_COWBOYS
)

# Run the game
game_result = simulator.simulate_game()
```

### Quick Demo (No Persistence)

```python
# Fast demo without database writes
demo_simulator = FullGameSimulator(
    away_team_id=TeamIDs.DETROIT_LIONS,
    home_team_id=TeamIDs.GREEN_BAY_PACKERS,
    enable_persistence=False  # No database overhead
)

game_result = demo_simulator.simulate_game()
```

## Persistence Control

The `FullGameSimulator` allows you to control whether game statistics are saved to the database.

### Constructor Control

```python
# Disable persistence at creation
simulator = FullGameSimulator(
    away_team_id=TeamIDs.KANSAS_CITY_CHIEFS,
    home_team_id=TeamIDs.LAS_VEGAS_RAIDERS,
    enable_persistence=False
)
```

### Property-Based Control

```python
# Start with any configuration
simulator = FullGameSimulator(away_team_id=7, home_team_id=9)

# Control persistence dynamically
simulator.persistence = False  # Disable persistence
simulator.persistence = True   # Re-enable persistence

# Check persistence status
if simulator.persistence:
    print("Statistics will be saved to database")
else:
    print("Statistics will not be saved (demo mode)")
```

### System Feedback

When persistence is enabled/disabled, you'll see clear feedback:

```
✅ Statistics persistence enabled (database: data/database/nfl_simulation.db, dynasty: default_dynasty)
🔄 Statistics persistence disabled
```

## Database Configuration

Control which database file is used for statistics persistence.

### Constructor Configuration

```python
# Set custom database at creation
simulator = FullGameSimulator(
    away_team_id=TeamIDs.BUFFALO_BILLS,
    home_team_id=TeamIDs.MIAMI_DOLPHINS,
    database_path="my_custom_season.db"
)
```

### Runtime Database Changes

```python
# Change database path during runtime
simulator = FullGameSimulator(away_team_id=7, home_team_id=9)

simulator.database_path = "dynasties/eagles.db"
# If persistence is enabled, service is automatically recreated

# Check current database
print(f"Current database: {simulator.database_path}")
```

### Special Database Types

```python
# In-memory database (perfect for testing)
test_simulator = FullGameSimulator(
    away_team_id=7,
    home_team_id=9,
    database_path=":memory:"
)

# Different database per season
season_2024 = FullGameSimulator(
    away_team_id=7,
    home_team_id=9,
    database_path="seasons/nfl_2024.db"
)
```

## Dynasty Context

Provide complete statistical isolation between different dynasties or users.

### Constructor Dynasty Setup

```python
# Set dynasty context at creation
eagles_dynasty = FullGameSimulator(
    away_team_id=TeamIDs.PHILADELPHIA_EAGLES,
    home_team_id=TeamIDs.DALLAS_COWBOYS,
    dynasty_id="eagles_championship_quest"
)
```

### Property-Based Dynasty Management

```python
# Start with default dynasty
simulator = FullGameSimulator(away_team_id=7, home_team_id=9)

# Change dynasty context
simulator.dynasty_id = "my_eagles_rebuild"
# If persistence is enabled, service is automatically recreated

# Check current dynasty
print(f"Current dynasty: {simulator.dynasty_id}")
```

### Dynasty Isolation

Each dynasty gets completely separate statistics:

```python
# Multiple dynasties with complete isolation
eagles_sim = FullGameSimulator(
    away_team_id=TeamIDs.PHILADELPHIA_EAGLES,
    home_team_id=TeamIDs.DALLAS_COWBOYS,
    dynasty_id="eagles_legacy"
)

chiefs_sim = FullGameSimulator(
    away_team_id=TeamIDs.KANSAS_CITY_CHIEFS,
    home_team_id=TeamIDs.LAS_VEGAS_RAIDERS,
    dynasty_id="chiefs_dynasty"
)

# These will have completely separate statistics!
```

## Advanced Patterns

### User's Preferred Workflow

The most flexible pattern for maximum control:

```python
# 1. Start with persistence disabled
simulator = FullGameSimulator(
    away_team_id=TeamIDs.DETROIT_LIONS,
    home_team_id=TeamIDs.GREEN_BAY_PACKERS,
    enable_persistence=False
)

# 2. Configure database and dynasty
simulator.database_path = "dynasties/lions_resurgence.db"
simulator.dynasty_id = "lions_rebuild_2024"

# 3. Enable persistence with all settings configured
simulator.persistence = True

# Result: Complete control over database and dynasty context
```

### Combined Configuration

```python
# All options together
simulator = FullGameSimulator(
    away_team_id=TeamIDs.CLEVELAND_BROWNS,
    home_team_id=TeamIDs.HOUSTON_TEXANS,
    overtime_type="playoffs",           # Playoff overtime rules
    enable_persistence=True,            # Enable statistics saving
    database_path="playoffs/2024.db",   # Custom database
    dynasty_id="browns_playoff_run"     # Dynasty context
)
```

### Runtime Reconfiguration

```python
# Change multiple settings during runtime
simulator.database_path = "new_season.db"
simulator.dynasty_id = "season_2025"
# Service automatically recreates with new settings if persistence enabled
```

## Common Use Cases

### 1. Dynasty Management

```python
# Separate database per dynasty
eagles_dynasty = FullGameSimulator(
    away_team_id=TeamIDs.PHILADELPHIA_EAGLES,
    home_team_id=TeamIDs.DALLAS_COWBOYS,
    database_path="dynasties/eagles.db",
    dynasty_id="eagles_championship_quest"
)

chiefs_dynasty = FullGameSimulator(
    away_team_id=TeamIDs.KANSAS_CITY_CHIEFS,
    home_team_id=TeamIDs.LAS_VEGAS_RAIDERS,
    database_path="dynasties/chiefs.db",
    dynasty_id="chiefs_threepeat"
)
```

### 2. Multi-User League

```python
# Multiple users, shared database, separate dynasties
user1 = FullGameSimulator(
    away_team_id=TeamIDs.BUFFALO_BILLS,
    home_team_id=TeamIDs.MIAMI_DOLPHINS,
    database_path="league_2024.db",
    dynasty_id="user1_bills_dynasty"
)

user2 = FullGameSimulator(
    away_team_id=TeamIDs.NEW_ENGLAND_PATRIOTS,
    home_team_id=TeamIDs.NEW_YORK_JETS,
    database_path="league_2024.db",
    dynasty_id="user2_patriots_dynasty"
)
```

### 3. Season Progression

```python
# Track progression through seasons
def create_season_simulator(year, dynasty_name):
    return FullGameSimulator(
        away_team_id=TeamIDs.SEATTLE_SEAHAWKS,
        home_team_id=TeamIDs.SAN_FRANCISCO_49ERS,
        database_path=f"seasons/nfl_{year}.db",
        dynasty_id=f"{dynasty_name}_season_{year}"
    )

# Different seasons
season_2024 = create_season_simulator(2024, "seahawks_rebuild")
season_2025 = create_season_simulator(2025, "seahawks_contenders")
```

### 4. Development and Testing

```python
# Development with in-memory database
dev_simulator = FullGameSimulator(
    away_team_id=TeamIDs.DETROIT_LIONS,
    home_team_id=TeamIDs.MINNESOTA_VIKINGS,
    database_path=":memory:",
    dynasty_id="dev_testing"
)

# Quick testing without persistence
test_simulator = FullGameSimulator(
    away_team_id=TeamIDs.CHICAGO_BEARS,
    home_team_id=TeamIDs.GREEN_BAY_PACKERS,
    enable_persistence=False
)
```

### 5. Game Type Separation

```python
# Regular season vs playoffs
def create_game_simulator(game_type, teams):
    database = "playoff_games.db" if game_type == "playoffs" else "regular_season.db"
    dynasty = f"my_dynasty_{game_type}"

    return FullGameSimulator(
        away_team_id=teams[0],
        home_team_id=teams[1],
        database_path=database,
        dynasty_id=dynasty,
        overtime_type=game_type
    )
```

## Troubleshooting

### Common Issues

#### 1. Persistence Not Working

```python
# Check persistence status
if not simulator.persistence:
    print("Persistence is disabled")
    simulator.persistence = True

# Check database path
print(f"Database: {simulator.database_path}")

# Check dynasty context
print(f"Dynasty: {simulator.dynasty_id}")
```

#### 2. Database Connection Issues

```python
# Try a different database path
simulator.database_path = "backup_database.db"

# Use in-memory database for testing
simulator.database_path = ":memory:"
```

#### 3. Dynasty Isolation Not Working

```python
# Ensure different dynasty IDs
sim1.dynasty_id = "dynasty_1"
sim2.dynasty_id = "dynasty_2"

# Verify dynasty context
print(f"Sim1 dynasty: {sim1.dynasty_id}")
print(f"Sim2 dynasty: {sim2.dynasty_id}")
```

### Error Messages

| Message | Meaning | Solution |
|---------|---------|----------|
| `⚠️ Statistics service initialization failed` | Database or service creation failed | Check database path and permissions |
| `⚠️ Failed to enable statistics persistence` | Could not enable persistence | Check database accessibility |
| `🔄 Statistics persistence disabled` | Persistence was turned off | Normal when disabling persistence |

### Best Practices

1. **Always check persistence status** before running important games
2. **Use descriptive dynasty IDs** for easier identification
3. **Create separate databases** for different projects/seasons
4. **Use in-memory databases** for testing and development
5. **Disable persistence** for quick demos and performance testing

## Complete Configuration Reference

```python
simulator = FullGameSimulator(
    away_team_id=TeamIDs.TEAM_NAME,      # Required: Away team (1-32)
    home_team_id=TeamIDs.TEAM_NAME,      # Required: Home team (1-32)
    overtime_type="regular_season",       # Optional: "regular_season" or "playoffs"
    enable_persistence=True,              # Optional: Enable/disable statistics saving
    database_path="custom.db",            # Optional: Custom database file path
    dynasty_id="my_dynasty"               # Optional: Dynasty context for isolation
)

# All properties can be changed at runtime:
simulator.persistence = True/False
simulator.database_path = "new_path.db"
simulator.dynasty_id = "new_dynasty"
```

This configuration system provides complete flexibility for managing NFL simulations across different contexts, users, and use cases while maintaining clear separation and control over data persistence.