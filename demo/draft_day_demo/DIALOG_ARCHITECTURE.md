# Draft Day Dialog Architecture

## Class: DraftDayDialog

**File**: `draft_day_dialog.py`

### Overview

PySide6/Qt dialog implementing interactive NFL draft simulation with:
- User-controlled draft picks
- AI-controlled CPU team picks
- Real-time UI updates
- Sortable prospects table
- Pick history tracking

### Inheritance

```python
DraftDayDialog(QDialog)
```

### Constructor

```python
def __init__(self, db_path: str, dynasty_id: str, season: int, user_team_id: int, parent=None)
```

**Parameters:**
- `db_path`: SQLite database path (use file-based, not `:memory:`)
- `dynasty_id`: Dynasty identifier string
- `season`: Draft year (e.g., 2026)
- `user_team_id`: User's team ID (1-32, use TeamIDs constants)
- `parent`: Parent widget (optional)

**Example:**
```python
from draft_day_dialog import DraftDayDialog
from constants.team_ids import TeamIDs

dialog = DraftDayDialog(
    db_path="data/database/nfl_simulation.db",
    dynasty_id="my_dynasty",
    season=2026,
    user_team_id=TeamIDs.DETROIT_LIONS,
    parent=main_window
)
dialog.exec()  # Modal
# or
dialog.show()  # Non-modal
```

## UI Layout Structure

### Top Section
```python
def _create_top_section(self) -> QHBoxLayout
```

Creates header with:
- Current pick label: "Round X, Pick Y (Overall: Z) - Team Name"
- User team label: "Your Team: Team Name"

### Middle Section
```python
def _create_middle_section(self) -> QSplitter
```

Creates 2-column splitter (70%/30%) with:
- **Left**: Prospects table (QTableWidget)
- **Right**: Team needs list (QListWidget)

### Button Section
```python
def _create_button_section(self) -> QHBoxLayout
```

Creates action buttons:
- **Make Pick**: Enabled only on user's turn, blue styling
- **Auto-Sim**: Always enabled (until draft complete), green styling

### History Section
```python
def _create_history_section(self) -> QTableWidget
```

Creates pick history table showing last 15 picks.

## UI Component Methods

### Prospects Table

```python
def populate_prospects_table(self)
```

**Purpose**: Load all undrafted prospects from database

**Columns:**
1. Rank (NumericTableWidgetItem)
2. Name (stores prospect_id in UserRole)
3. Pos
4. College
5. Overall (NumericTableWidgetItem, color-coded)
6. Potential (NumericTableWidgetItem)

**Color Coding:**
- Green: Overall >= 85 (elite)
- Blue: Overall >= 75 (high)
- Red: Overall < 65 (low)
- Default: 65-74 (mid)

**Sorting:**
- Uses NumericTableWidgetItem for proper numeric sorting
- Default sort: Rank ascending

### Team Needs List

```python
def populate_team_needs(self)
```

**Purpose**: Display user team's positional needs

**Format**: `POSITION - URGENCY_LEVEL`

**Color Coding:**
- Red: Priority 1 (critical)
- Yellow: Priority 2 (high)
- Gray: Priority 3+ (moderate)

### Pick History Table

```python
def populate_pick_history(self)
```

**Purpose**: Show last 15 picks made

**Columns:**
1. Pick (overall pick number)
2. Round
3. Team (team name from TeamLoader)
4. Player (first + last name)
5. Pos

**Data Source**: Last 15 entries from `self.draft_order` where `is_made == True`

## Draft Flow Methods

### Initialize Draft Order

```python
def _load_draft_order(self)
```

**Purpose**: Load complete draft order from database into memory

**Data Structure:**
```python
self.draft_order = [
    {
        'round': int,
        'overall': int,
        'team_id': int,
        'pick_in_round': int,
        'prospect_id': Optional[str],
        'is_made': bool
    },
    ...
]
```

**State Tracking:**
- `self.current_pick_index`: Index of current pick in draft_order
- `self.is_draft_complete`: Boolean flag for draft completion

### Advance to Next Pick

```python
def advance_to_next_pick(self)
```

**Purpose**: Move to next pick and determine if user or CPU turn

**Logic:**
1. Check if draft complete
2. Get current pick from `self.draft_order[self.current_pick_index]`
3. If user's team: Enable "Make Pick" button
4. If CPU team: Disable "Make Pick", schedule `execute_cpu_pick()` after 1 second

**Timer Usage:**
```python
QTimer.singleShot(1000, self.execute_cpu_pick)  # 1 second delay
```

### Execute User Pick

```python
def on_make_pick_clicked(self)
```

**Purpose**: Handle user's draft selection

**Steps:**
1. Get selected row from `prospects_table`
2. Extract `prospect_id` from Name column's UserRole
3. Validate selection (show warning if none)
4. Call `_execute_pick(prospect_id, current_pick)`
5. Increment `current_pick_index`
6. Refresh UI
7. Advance to next pick

**Validation:**
- Shows QMessageBox warning if no prospect selected

### Execute CPU Pick

```python
def execute_cpu_pick(self)
```

**Purpose**: AI makes a pick for CPU team

**Current AI Logic** (simplified):
1. Query best available prospect by overall_rating + potential_rating
2. Select top prospect
3. Execute pick via `_execute_pick()`
4. Increment `current_pick_index`
5. Refresh UI

**Note**: This is simplified. See `draft_day_demo.py` for sophisticated AI with:
- GM personality-based decisions
- Team needs weighting
- BPA vs. need tendency
- Potential valuation

### Execute Pick (Database Update)

```python
def _execute_pick(self, prospect_id: str, pick_info: Dict[str, Any])
```

**Purpose**: Update database and local state for a pick

**Database Operations:**
1. Update `draft_prospects`:
   ```sql
   SET is_drafted = 1, drafted_by_team_id = ?, drafted_round = ?, drafted_pick = ?
   ```

2. Update `draft_order`:
   ```sql
   SET prospect_id = ?, pick_made_at = datetime('now')
   ```

3. Commit transaction

**Local State Update:**
```python
pick_info['prospect_id'] = prospect_id
pick_info['is_made'] = True
```

## Auto-Simulation Methods

### Auto-Sim Trigger

```python
def on_auto_sim_clicked(self)
```

**Purpose**: Start auto-simulation to user's next pick

**Steps:**
1. Disable both buttons
2. Call `_auto_sim_next_pick()` to start recursive simulation

### Auto-Sim Recursive Loop

```python
def _auto_sim_next_pick(self)
```

**Purpose**: Recursively simulate picks until user's turn

**Logic:**
1. Check if draft complete → stop, show message
2. Check if user's turn → stop, enable buttons
3. If CPU turn:
   - Execute CPU pick
   - Schedule next iteration after 500ms: `QTimer.singleShot(500, self._auto_sim_next_pick)`

**Speed**: 500ms between picks (adjustable)

## UI Refresh Methods

### Refresh All UI

```python
def refresh_all_ui(self)
```

**Purpose**: Update all UI components after pick

**Updates:**
1. Current pick label text
2. Prospects table (removes drafted prospects)
3. Team needs list
4. Pick history table (adds new pick)
5. Button states (Make Pick enabled/disabled based on turn)

**Draft Complete Handling:**
- Sets label to "DRAFT COMPLETE"
- Disables all buttons

## Draft Completion

### Show Completion Message

```python
def _show_draft_complete_message(self)
```

**Purpose**: Display summary dialog when draft ends

**Information Shown:**
- Total picks made
- User's team pick count
- Confirmation message

**Implementation:**
```python
QMessageBox.information(self, "Draft Complete", message)
```

## Helper Class: NumericTableWidgetItem

**File**: `draft_day_dialog.py` (embedded)

### Purpose

Custom QTableWidgetItem for proper numeric sorting.

### Problem Solved

Standard QTableWidgetItem sorts strings lexicographically:
- "1", "10", "2", "20" → sorts as 1, 10, 2, 20 (wrong)

NumericTableWidgetItem sorts numerically:
- "1", "10", "2", "20" → sorts as 1, 2, 10, 20 (correct)

### Usage

```python
# Create item with display text
rank_item = NumericTableWidgetItem(str(rank))

# Store numeric value in UserRole for sorting
rank_item.setData(Qt.UserRole, rank)

# Add to table
table.setItem(row, column, rank_item)
```

### Implementation

```python
def __lt__(self, other: QTableWidgetItem) -> bool:
    """Compare items numerically using UserRole data."""
    self_value = self.data(Qt.UserRole)
    other_value = other.data(Qt.UserRole)

    if self_value is not None and other_value is not None:
        try:
            return float(self_value) < float(other_value)
        except (ValueError, TypeError):
            pass

    return super().__lt__(other)
```

## Database Schema Dependencies

### Required Tables

1. **draft_prospects**: Prospect data with is_drafted flag
2. **draft_order**: Pick order with prospect_id foreign key
3. **team_needs**: Team positional needs (optional, for display only)
4. **gm_personalities**: GM traits (not used in dialog, used in demo AI)

### Key Columns

**draft_prospects:**
- `prospect_id` (PK)
- `dynasty_id`
- `first_name`, `last_name`
- `position`, `college`
- `overall_rating`, `potential_rating`
- `is_drafted`, `drafted_by_team_id`, `drafted_round`, `drafted_pick`

**draft_order:**
- `dynasty_id`
- `round_number`, `pick_in_round`, `overall_pick`
- `current_team_id`, `prospect_id`
- `pick_made_at`

**team_needs:**
- `team_id`, `dynasty_id`
- `position`, `priority`, `urgency_level`

## Integration Notes

### Integrating into Main Application

1. **Import Dialog:**
   ```python
   from demo.draft_day_demo.draft_day_dialog import DraftDayDialog
   ```

2. **Launch Modal Dialog:**
   ```python
   dialog = DraftDayDialog(
       db_path=self.db_path,
       dynasty_id=self.dynasty_id,
       season=self.current_season,
       user_team_id=self.user_team_id,
       parent=self
   )
   dialog.exec()  # Blocks until closed
   ```

3. **Launch Non-Modal Dialog:**
   ```python
   dialog.show()  # Returns immediately
   ```

### Database Requirements

- Must use **file-based database**, not `:memory:`
- Database must have all required tables populated
- Draft order must be pre-generated before opening dialog

### Team Name Resolution

Dialog uses `team_loader.get_team_by_id()` for team names. Ensure team_loader is properly initialized:

```python
from team_management.teams.team_loader import get_team_by_id

team = get_team_by_id(team_id)
team_name = team.name if team else f"Team {team_id}"
```

## Performance Considerations

### Database Queries

Dialog makes frequent queries:
- `populate_prospects_table()`: Queries all undrafted prospects
- `populate_pick_history()`: Queries last 15 picks
- Each pick: 2 UPDATE queries + 1 COMMIT

**Optimization**: Queries are simple and fast (indexed on `dynasty_id` and `is_drafted`).

### UI Refresh

`refresh_all_ui()` called after every pick:
- Clears and repopulates 3 tables
- Can cause flicker on large datasets

**Optimization**: Could use incremental updates (add/remove single row) instead of full refresh.

### Auto-Sim Speed

500ms between picks during auto-simulation:
- Adjustable via `QTimer.singleShot(500, ...)`
- Faster = less readable, Slower = more tedious
- 500ms provides good balance

## Known Limitations

1. **Simplified AI**: CPU picks best available, doesn't consider:
   - Positional value curves
   - Draft strategy (run on positions)
   - GM risk tolerance
   - See `draft_day_demo.py` for sophisticated AI

2. **No Trade Support**: Cannot trade draft picks during simulation

3. **No Pick Timer**: No countdown clock visualization

4. **Full Table Refresh**: UI flickers on each pick due to complete table repopulation

5. **In-Memory DB Issues**: Dialog requires file-based database for proper persistence

## Future Enhancements

### High Priority

- [ ] Integrate sophisticated AI from `draft_day_demo.py`
- [ ] Incremental UI updates (avoid full refresh)
- [ ] Draft pick trades dialog

### Medium Priority

- [ ] Prospect detail view on double-click (use existing `ProspectDetailDialog`)
- [ ] Pick countdown timer visualization
- [ ] War room notes/ratings for prospects

### Low Priority

- [ ] Multiple draft board views (position filters)
- [ ] Export draft results to CSV/JSON
- [ ] Save/load draft in progress
- [ ] Draft grade analysis on completion

## Testing

### Unit Testing

Dialog is primarily UI, difficult to unit test. Focus on:
- Database operations (`_execute_pick()`)
- Draft state management (`_load_draft_order()`)
- AI logic (`execute_cpu_pick()`)

### Integration Testing

Use `launch_dialog.py` for manual integration testing:
1. Verify all prospects load
2. Test user pick flow
3. Test auto-simulation
4. Verify pick history updates
5. Confirm draft completion message

### Edge Cases

- What if no prospects available? (should not happen)
- What if database connection fails? (dialog will error)
- What if user closes dialog mid-draft? (`closeEvent` closes connection cleanly)

## Troubleshooting

### "No prospects available"

Check database:
```sql
SELECT COUNT(*) FROM draft_prospects WHERE dynasty_id = ? AND is_drafted = 0;
```

### "Make Pick button always disabled"

Check `current_team_id` in draft_order matches `user_team_id`.

### "UI not refreshing"

Check console for database errors. Ensure `refresh_all_ui()` is called after picks.

### "Team names showing as 'Team X'"

Normal fallback when `get_team_by_id()` returns None. Ensure team_loader is initialized.
