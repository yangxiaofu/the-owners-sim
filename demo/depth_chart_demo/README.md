# Depth Chart API Interactive Demo

Terminal-based interactive demo for exploring all depth chart API methods with isolated database and mock data.

## Quick Start

```bash
# 1. Navigate to demo directory
cd demo/depth_chart_demo

# 2. Set up demo database with mock data
PYTHONPATH=../../src python demo_database_setup.py

# 3. Run interactive demo
PYTHONPATH=../../src python depth_chart_demo.py
```

## Overview

This demo provides a hands-on environment to explore all 19 depth chart API methods without affecting your main game database. It includes:

- **Isolated Database**: `demo.db` completely separate from production data
- **Mock Data**: 2 teams × ~53 players = 106 mock players
- **Interactive Menu**: 20 menu options covering all API methods
- **Before/After Visualization**: See changes immediately
- **Reset Capability**: Restore original data anytime

## Mock Data

### Team 9 - Detroit Lions (Depth Charts Assigned)
- All positions have proper depth charts (1, 2, 3...)
- Use for testing **modifications** (swap, reorder, set starter, etc.)
- Demonstrates a "good state" depth chart

### Team 3 - Chicago Bears (Unassigned Depth Charts)
- All players have `depth_chart_order = 99` (unassigned)
- Use for testing **auto-generation** and **validation**
- Demonstrates a "bad state" depth chart

### Positions Covered
- **Offense**: QB (3), RB (4), WR (6), TE (3), OL (8)
- **Defense**: DL (6), LB (5), DB (6)
- **Special Teams**: K (1), P (1), LS (1)

## Menu Structure

### Core Retrieval Methods (1-4)
- **Get Position Depth Chart**: View depth chart for specific position (QB, RB, etc.)
- **Get Full Depth Chart**: View all positions at once
- **Get Starter**: Check who is starter for a position
- **Get Backups**: View all backups for a position

### Modification Methods (5-9)
- **Set Starter**: Promote player to depth #1 (starter)
- **Set Backup**: Assign player to specific backup depth (2, 3, 4...)
- **Swap Depth Positions**: Swap two players' depth orders
- **Reorder Position Depth**: Complete reordering of position (drag-and-drop simulation)
- **Remove From Depth Chart**: Set player to unassigned (depth 99)

### Batch Operations (10-12)
- **Auto-Generate Depth Chart**: Sort ALL positions by overall rating
- **Reset Position Depth Chart**: Reset single position to auto-generated order
- **Clear Depth Chart**: Set ALL players to unassigned (depth 99)

### Validation Methods (13-15)
- **Validate Depth Chart**: Show all errors and warnings
- **Has Starter**: Check if position has starter assigned
- **Get Depth Chart Gaps**: Find all positions missing starters

### Position Constraints (16-17)
- **Get Position Requirements**: Show min/recommended depth per position
- **Check Depth Chart Compliance**: Verify all positions meet minimum requirements

### Settings & Utilities (18-20)
- **Switch Team**: Toggle between Lions (depth charts set) and Bears (unassigned)
- **Reset Demo Database**: Restore original mock data
- **View Database Stats**: See player counts, depth chart assignments

## Example Workflows

### Scenario 1: Understanding Auto-Generation

```
1. Start with Team 3 (Bears) - all unassigned
2. Select "13. Validate Depth Chart" → See errors for missing starters
3. Select "10. Auto-Generate Depth Chart" → Fix all issues
4. Select "13. Validate Depth Chart" → See no errors
5. Select "2. Get Full Depth Chart" → View auto-generated assignments
```

### Scenario 2: Manual Depth Chart Management

```
1. Start with Team 9 (Lions) - depth charts already set
2. Select "1. Get Position Depth Chart" → View QB depth
3. Select "5. Set Starter" → Promote backup QB to starter
4. Select "1. Get Position Depth Chart" → See changes applied
5. Select "7. Swap Depth Positions" → Swap two RBs
```

### Scenario 3: Position-Specific Operations

```
1. Select "1. Get Position Depth Chart" → Enter "running_back"
2. See all RBs with depth assignments
3. Select "9. Remove From Depth Chart" → Remove RB3
4. Select "11. Reset Position Depth Chart" → Restore to auto-generated
5. Select "1. Get Position Depth Chart" → Verify reset worked
```

### Scenario 4: Validation and Compliance

```
1. Select "12. Clear Depth Chart" → Set all to unassigned
2. Select "15. Get Depth Chart Gaps" → See all positions missing starters
3. Select "17. Check Depth Chart Compliance" → See non-compliant positions
4. Select "10. Auto-Generate Depth Chart" → Fix everything
5. Select "17. Check Depth Chart Compliance" → All compliant
```

## API Methods Demonstrated

All 19 depth chart API methods are available:

| Method | Menu Option | Description |
|--------|-------------|-------------|
| `get_position_depth_chart()` | 1 | Get depth chart for specific position |
| `get_full_depth_chart()` | 2 | Get complete depth chart (all positions) |
| `get_starter()` | 3 | Get starter for position |
| `get_backups()` | 4 | Get backups for position |
| `set_starter()` | 5 | Set player as starter (depth 1) |
| `set_backup()` | 6 | Set player as backup at specific depth |
| `swap_depth_positions()` | 7 | Swap two players' depth orders |
| `reorder_position_depth()` | 8 | Complete reordering of position |
| `remove_from_depth_chart()` | 9 | Set player to unassigned (depth 99) |
| `auto_generate_depth_chart()` | 10 | Auto-assign all by overall rating |
| `reset_position_depth_chart()` | 11 | Reset single position to auto-generated |
| `clear_depth_chart()` | 12 | Set all to unassigned (depth 99) |
| `validate_depth_chart()` | 13 | Get errors and warnings |
| `has_starter()` | 14 | Check if position has starter |
| `get_depth_chart_gaps()` | 15 | Find positions missing starters |
| `get_position_requirements()` | 16 | Get min/recommended depth per position |
| `check_depth_chart_compliance()` | 17 | Verify minimum requirements met |

## Database Schema

The demo database (`demo.db`) contains:

### dynasties table
```sql
CREATE TABLE dynasties (
    dynasty_id TEXT PRIMARY KEY,
    team_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
```

### players table
```sql
CREATE TABLE players (
    dynasty_id TEXT NOT NULL,
    player_id INTEGER NOT NULL,
    source_player_id TEXT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    number INTEGER,
    team_id INTEGER NOT NULL,
    positions TEXT NOT NULL,  -- JSON array
    attributes TEXT NOT NULL,  -- JSON object
    status TEXT DEFAULT 'active',
    years_pro INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (dynasty_id, player_id)
)
```

### team_rosters table
```sql
CREATE TABLE team_rosters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    team_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    depth_chart_order INTEGER DEFAULT 99,  -- Lower = higher on depth chart
    roster_status TEXT DEFAULT 'active',
    joined_date TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(dynasty_id, team_id, player_id)
)
```

## Position Names Reference

Use these exact position names when prompted:

### Offense
- `quarterback`, `running_back`, `wide_receiver`, `tight_end`
- `left_tackle`, `left_guard`, `center`, `right_guard`, `right_tackle`

### Defense
- `defensive_end`, `defensive_tackle`, `nose_tackle`
- `linebacker`
- `cornerback`, `safety`

### Special Teams
- `kicker`, `punter`, `long_snapper`

## Troubleshooting

### Database Not Found
```
❌ Demo database not found!
Please run: python demo_database_setup.py
```
**Solution**: Run `PYTHONPATH=../../src python demo_database_setup.py`

### Invalid Position
```
⚠️  No players found for position 'qb'
```
**Solution**: Use full position name: `quarterback` (not `qb`)

### Player Not Found
```
❌ Failed to set starter (check if player plays this position)
```
**Solution**: Verify player_id is correct and player plays that position

### Import Errors
```
ModuleNotFoundError: No module named 'depth_chart'
```
**Solution**: Always use `PYTHONPATH=../../src` prefix when running demo

## Tips

1. **Start with Team 3 (Bears)** if you want to see validation errors and test auto-generation
2. **Use Team 9 (Lions)** if you want to practice modifications on existing depth charts
3. **Reset database** anytime with option 19 to restore original mock data
4. **Switch between teams** (option 18) to see different states
5. **View stats** (option 20) to see current database state

## Files

- `depth_chart_demo.py` - Main interactive demo script
- `demo_database_setup.py` - Database initialization with mock data
- `demo.db` - SQLite database (auto-generated, not in git)
- `README.md` - This file

## Next Steps

After exploring the demo:
1. Understand the API patterns for UI integration
2. See how before/after states are visualized
3. Learn validation error messages
4. Plan UI implementation based on API capabilities
