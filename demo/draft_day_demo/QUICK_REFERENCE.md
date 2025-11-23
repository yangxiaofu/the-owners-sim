# Draft Day Dialog - Quick Reference

## Launch Demo

```bash
cd demo/draft_day_demo
python launch_dialog.py
```

## Basic Integration

```python
from demo.draft_day_demo.draft_day_dialog import DraftDayDialog
from constants.team_ids import TeamIDs

dialog = DraftDayDialog(
    db_path="data/database/nfl_simulation.db",
    dynasty_id="my_dynasty",
    season=2026,
    user_team_id=TeamIDs.DETROIT_LIONS,
    parent=self
)

dialog.exec()  # Modal
# or
dialog.show()  # Non-modal
```

## Key Files

| File | Purpose |
|------|---------|
| `draft_day_dialog.py` | Main dialog implementation |
| `launch_dialog.py` | Demo launcher with temp DB |
| `README_DIALOG.md` | User guide |
| `DIALOG_ARCHITECTURE.md` | Technical documentation |
| `IMPLEMENTATION_SUMMARY.md` | Implementation overview |

## UI Components

### Prospects Table
- **Columns**: Rank, Name, Pos, College, Overall, Potential
- **Sortable**: Click headers
- **Color**: Green (85+), Blue (75-84), Red (<65)
- **Selection**: Click row → Make Pick

### Team Needs
- **Format**: `POSITION - URGENCY`
- **Color**: Red (P1), Yellow (P2), Gray (P3+)

### Buttons
- **Make Pick**: User's turn only (blue)
- **Auto-Sim**: Simulate to next pick (green)

### Pick History
- **Displays**: Last 15 picks
- **Columns**: Pick, Round, Team, Player, Pos

## Key Methods

| Method | Purpose |
|--------|---------|
| `populate_prospects_table()` | Load available prospects |
| `populate_team_needs()` | Load user team needs |
| `populate_pick_history()` | Load recent picks |
| `advance_to_next_pick()` | Move to next pick |
| `on_make_pick_clicked()` | User selects prospect |
| `execute_cpu_pick()` | AI makes pick |
| `on_auto_sim_clicked()` | Start auto-simulation |
| `refresh_all_ui()` | Update all components |

## Database Requirements

### Required Tables
- `draft_prospects` - Prospect data
- `draft_order` - Pick order
- `team_needs` - Team needs (optional)

### Key Columns

**draft_prospects:**
```sql
prospect_id, dynasty_id, first_name, last_name,
position, college, overall_rating, potential_rating,
is_drafted, drafted_by_team_id, drafted_round, drafted_pick
```

**draft_order:**
```sql
dynasty_id, round_number, pick_in_round, overall_pick,
current_team_id, prospect_id, pick_made_at
```

## Configuration

### Change User Team
```python
user_team_id = TeamIDs.PHILADELPHIA_EAGLES  # Any team 1-32
```

### Change Draft Year
```python
season = 2027
```

### Adjust CPU Pick Delay
```python
# In draft_day_dialog.py, line ~455
QTimer.singleShot(1000, self.execute_cpu_pick)  # Change 1000
```

### Adjust Auto-Sim Speed
```python
# In draft_day_dialog.py, line ~485
QTimer.singleShot(500, self._auto_sim_next_pick)  # Change 500
```

## Common Issues

### Import Errors
```bash
pip install -r requirements-ui.txt
```

### In-Memory DB Issues
Use file-based database, not `:memory:`

### No Prospects Show
Check database:
```sql
SELECT COUNT(*) FROM draft_prospects
WHERE dynasty_id = ? AND is_drafted = 0;
```

### Make Pick Always Disabled
Verify `current_team_id` in `draft_order` matches `user_team_id`

## Testing

```bash
# Test imports
cd demo/draft_day_demo
python -c "from draft_day_dialog import DraftDayDialog; print('OK')"

# Launch demo
python launch_dialog.py
```

## Documentation Files

1. **README_DIALOG.md** - Complete usage guide
2. **DIALOG_ARCHITECTURE.md** - Technical architecture
3. **IMPLEMENTATION_SUMMARY.md** - Implementation details
4. **QUICK_REFERENCE.md** - This file

## Quick Stats

- **Dialog Size**: 1000x700 pixels
- **Lines of Code**: 750+ (draft_day_dialog.py)
- **Methods**: 25+ methods
- **CPU Pick Delay**: 1 second
- **Auto-Sim Speed**: 500ms per pick
- **Pick History**: Last 15 picks
- **Prospects Shown**: All undrafted (up to 300)

## Color Codes

### Prospect Ratings
- 🟢 Green: Elite (85+)
- 🔵 Blue: High (75-84)
- ⚫ Black: Mid (65-74)
- 🔴 Red: Low (<65)

### Team Needs
- 🔴 Red: Priority 1 (Critical)
- 🟡 Yellow: Priority 2 (High)
- ⚫ Gray: Priority 3+ (Moderate)

## Button States

| Button | Enabled When | Color |
|--------|--------------|-------|
| Make Pick | User's turn | Blue |
| Auto-Sim | Not complete | Green |

## Pro Tips

1. **Fast Draft**: Use Auto-Sim repeatedly
2. **Review Picks**: Check Pick History table
3. **Sort Prospects**: Click column headers
4. **Check Needs**: Reference Team Needs list
5. **Close Safely**: Dialog cleans up database connection

## See Also

- CLI version: `draft_day_demo.py`
- Prospect widget: `ui/widgets/draft_prospects_widget.py`
- Detail dialog: `ui/dialogs/prospect_detail_dialog.py`
