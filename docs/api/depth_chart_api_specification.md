# Depth Chart API Specification

## Overview

The Depth Chart API provides complete functionality for managing NFL team depth charts, including setting starters, reordering positions, and retrieving depth chart data. This system integrates with the existing `team_rosters` table using the `depth_chart_order` field.

## Database Schema Reference

```sql
-- Existing team_rosters table structure
CREATE TABLE team_rosters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    team_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    depth_chart_order INTEGER DEFAULT 99,  -- Lower = higher on depth chart (1 = starter, 2 = backup, etc.)
    roster_status TEXT DEFAULT 'active',
    joined_date TEXT,
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, team_id, player_id)
)
```

## File Structure

```
src/depth_chart/
├── __init__.py
├── depth_chart_api.py          # Database API layer (CRUD operations)
├── depth_chart_manager.py      # Business logic layer (validation, calculations)
├── depth_chart_validator.py    # Position validation and constraints
└── depth_chart_types.py        # Type definitions and constants
```

## API Methods

### 1. Core Retrieval Methods

#### `get_position_depth_chart(dynasty_id: str, team_id: int, position: str) -> List[Dict[str, Any]]`
**Purpose**: Get depth chart for a specific position, ordered by depth_chart_order

**Returns**:
```python
[
    {
        'player_id': 1234,
        'player_name': 'Jared Goff',
        'depth_chart_order': 1,  # Starter
        'overall': 85,
        'age': 29,
        'jersey_number': 16
    },
    {
        'player_id': 5678,
        'player_name': 'Hendon Hooker',
        'depth_chart_order': 2,  # Backup
        'overall': 72,
        'age': 26,
        'jersey_number': 2
    }
]
```

#### `get_full_depth_chart(dynasty_id: str, team_id: int) -> Dict[str, List[Dict[str, Any]]]`
**Purpose**: Get complete depth chart for all positions

**Returns**:
```python
{
    'QB': [...],
    'RB': [...],
    'WR': [...],
    'TE': [...],
    # ... all positions
}
```

#### `get_starter(dynasty_id: str, team_id: int, position: str) -> Optional[Dict[str, Any]]`
**Purpose**: Get the starter (depth_chart_order = 1) for a specific position

**Returns**: Player dict or None if no starter assigned

#### `get_backups(dynasty_id: str, team_id: int, position: str) -> List[Dict[str, Any]]`
**Purpose**: Get all backups (depth_chart_order > 1) for a position, ordered by depth

### 2. Depth Chart Modification Methods

#### `set_starter(dynasty_id: str, team_id: int, player_id: int, position: str) -> bool`
**Purpose**: Set a player as starter for their position (depth_chart_order = 1)

**Behavior**:
- Sets target player's depth_chart_order to 1
- Shifts previous starter to depth_chart_order = 2
- Shifts all other players down by 1
- Validates player plays this position

**Returns**: True if successful, False otherwise

#### `set_backup(dynasty_id: str, team_id: int, player_id: int, position: str, backup_order: int = 2) -> bool`
**Purpose**: Set a player as backup at specific depth (default = 2)

**Behavior**:
- Sets player's depth_chart_order to specified backup_order
- Shifts players at/below that order down by 1
- Does NOT affect the starter (order 1)

#### `swap_depth_positions(dynasty_id: str, team_id: int, player1_id: int, player2_id: int) -> bool`
**Purpose**: Swap depth chart positions between two players on same position

**Behavior**:
- Validates both players play same position
- Swaps their depth_chart_order values atomically
- Useful for promoting backup to starter, etc.

#### `reorder_position_depth(dynasty_id: str, team_id: int, position: str, ordered_player_ids: List[int]) -> bool`
**Purpose**: Complete reordering of depth chart for a position

**Behavior**:
- Sets depth_chart_order sequentially (1, 2, 3, ...) based on ordered_player_ids list
- First player in list becomes starter (order 1)
- Validates all players play this position
- Atomic operation (all or nothing)

**Example**:
```python
# Make Hooker the starter, Goff the backup
reorder_position_depth(dynasty_id, team_id, 'QB', [5678, 1234])
# Result: Hooker = 1, Goff = 2
```

#### `remove_from_depth_chart(dynasty_id: str, team_id: int, player_id: int) -> bool`
**Purpose**: Remove player from depth chart (set depth_chart_order to 99)

**Behavior**:
- Sets player's depth_chart_order to 99 (default/unassigned)
- Compacts remaining players (if player was at order 2, order 3 becomes 2, etc.)
- Does NOT remove from roster (only depth chart)

### 3. Batch Operations

#### `auto_generate_depth_chart(dynasty_id: str, team_id: int) -> bool`
**Purpose**: Automatically generate depth chart based on player overalls

**Behavior**:
- For each position, orders players by overall rating (highest first)
- Assigns depth_chart_order sequentially (1 = highest overall, 2 = second highest, etc.)
- Useful for new dynasties or roster resets

#### `reset_position_depth_chart(dynasty_id: str, team_id: int, position: str) -> bool`
**Purpose**: Reset a single position's depth chart to auto-generated (by overall)

#### `clear_depth_chart(dynasty_id: str, team_id: int) -> bool`
**Purpose**: Set all players on team to depth_chart_order = 99 (unassigned)

### 4. Validation Methods

#### `validate_depth_chart(dynasty_id: str, team_id: int) -> Dict[str, List[str]]`
**Purpose**: Validate entire depth chart and return issues

**Returns**:
```python
{
    'errors': [
        'QB position has no starter',
        'RB has 2 players at depth_chart_order = 1',
    ],
    'warnings': [
        'OT only has 1 player on depth chart',
        'FS has no backup assigned'
    ]
}
```

#### `has_starter(dynasty_id: str, team_id: int, position: str) -> bool`
**Purpose**: Check if position has a starter assigned

#### `get_depth_chart_gaps(dynasty_id: str, team_id: int) -> Dict[str, int]`
**Purpose**: Identify positions without starters

**Returns**:
```python
{
    'QB': 0,  # Has starter
    'RB': 0,  # Has starter
    'FS': 1,  # Missing starter
    'SS': 1   # Missing starter
}
```

### 5. Position Constraint Methods

#### `get_position_requirements() -> Dict[str, Dict[str, int]]`
**Purpose**: Get minimum/recommended depth chart sizes per position

**Returns**:
```python
{
    'QB': {'minimum': 1, 'recommended': 3},
    'RB': {'minimum': 2, 'recommended': 4},
    'WR': {'minimum': 3, 'recommended': 6},
    'OT': {'minimum': 2, 'recommended': 3},
    # ... etc
}
```

#### `check_depth_chart_compliance(dynasty_id: str, team_id: int) -> Dict[str, bool]`
**Purpose**: Check if depth chart meets minimum requirements

**Returns**:
```python
{
    'QB': True,   # Meets minimum (1+ players)
    'RB': True,   # Meets minimum (2+ players)
    'FS': False,  # Does NOT meet minimum (0 players)
}
```

## Integration Example

### Setting a Starter (UI → Controller → Domain Model → API)

```python
# ui/controllers/team_controller.py
def set_player_as_starter(self, player_id: int, position: str):
    """Set player as starter for their position."""
    success = self.team_model.set_depth_chart_starter(
        team_id=self.current_team_id,
        player_id=player_id,
        position=position
    )

    if success:
        # Reload roster to reflect changes
        self.load_team_roster()
        return True
    else:
        print(f"[ERROR] Failed to set player {player_id} as starter")
        return False

# ui/domain_models/team_data_model.py
def set_depth_chart_starter(self, team_id: int, player_id: int, position: str) -> bool:
    """Set player as starter via depth chart API."""
    from depth_chart.depth_chart_api import DepthChartAPI

    depth_chart_api = DepthChartAPI(self.db_path)
    return depth_chart_api.set_starter(
        dynasty_id=self.dynasty_id,
        team_id=team_id,
        player_id=player_id,
        position=position
    )

# src/depth_chart/depth_chart_api.py
def set_starter(self, dynasty_id: str, team_id: int, player_id: int, position: str) -> bool:
    """Set player as starter (depth_chart_order = 1)."""
    from depth_chart.depth_chart_manager import DepthChartManager

    # Validate player plays this position
    manager = DepthChartManager(self.db_path)
    if not manager.validate_player_position(dynasty_id, team_id, player_id, position):
        print(f"[ERROR] Player {player_id} does not play {position}")
        return False

    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()

    try:
        # Step 1: Get current starter (if exists)
        cursor.execute('''
            SELECT player_id FROM team_rosters
            WHERE dynasty_id = ? AND team_id = ?
            AND player_id IN (
                SELECT player_id FROM players WHERE primary_position = ?
            )
            AND depth_chart_order = 1
        ''', (dynasty_id, team_id, position))

        current_starter = cursor.fetchone()

        # Step 2: Shift current starter to backup (order 2)
        if current_starter:
            cursor.execute('''
                UPDATE team_rosters
                SET depth_chart_order = 2
                WHERE dynasty_id = ? AND team_id = ? AND player_id = ?
            ''', (dynasty_id, team_id, current_starter[0]))

        # Step 3: Set new player as starter (order 1)
        cursor.execute('''
            UPDATE team_rosters
            SET depth_chart_order = 1
            WHERE dynasty_id = ? AND team_id = ? AND player_id = ?
        ''', (dynasty_id, team_id, player_id))

        conn.commit()
        print(f"✅ Set player {player_id} as starter for {position}")
        return True

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Failed to set starter: {e}")
        return False
    finally:
        conn.close()
```

## Error Handling

All API methods should handle:
1. **Database errors**: Connection failures, constraint violations
2. **Validation errors**: Invalid positions, player not on roster
3. **Dynasty isolation**: Ensure all operations respect dynasty_id
4. **Atomic operations**: Use transactions for multi-step updates

## Testing Checklist

- [ ] Set starter for each position (QB, RB, WR, etc.)
- [ ] Swap starter and backup
- [ ] Reorder complete position depth chart
- [ ] Auto-generate depth chart for new dynasty
- [ ] Validate depth chart identifies missing starters
- [ ] Remove player from depth chart (compaction works)
- [ ] Batch operations handle errors gracefully
- [ ] Dynasty isolation prevents cross-dynasty contamination