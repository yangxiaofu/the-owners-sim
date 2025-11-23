# Draft Day Dialog - Interactive UI Demo

Interactive PySide6/Qt dialog for NFL draft simulation with AI decision-making.

## Overview

The Draft Day Dialog provides a complete interactive UI for simulating the NFL draft:

- **Available Prospects Table**: Sortable table of all undrafted prospects with ratings
- **Team Needs Display**: Shows your team's positional needs and priorities
- **User Pick Controls**: Make selections when it's your turn
- **Auto-Simulation**: Automatically simulate to your next pick
- **Pick History**: View the last 15 picks made
- **AI Decision Making**: CPU teams make realistic picks based on BPA and team needs

## Files

- `draft_day_dialog.py` - Main dialog implementation (DraftDayDialog class)
- `launch_dialog.py` - Demo launcher with temporary database
- `test_dialog.py` - Simple test script (has in-memory DB limitations)
- `database_setup.py` - Database schema creation (shared with CLI demo)
- `mock_data_generator.py` - Mock prospect/GM/need generation (shared with CLI demo)

## Quick Start

### Launch Interactive Dialog

```bash
# Install UI dependencies (if not already installed)
pip install -r requirements-ui.txt

# Launch dialog (from project root)
cd demo/draft_day_demo
python launch_dialog.py
```

This will:
1. Create a temporary SQLite database
2. Generate 300 mock prospects
3. Create GM personalities and team needs for all 32 teams
4. Generate draft order for 7 rounds (262 picks)
5. Launch the interactive dialog with Detroit Lions as user team

## Dialog Features

### UI Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Round X, Pick Y (Overall: Z) - Team Name    Your Team: ...  │
├─────────────────────────────────┬───────────────────────────┤
│ Available Prospects             │ Team Needs                │
│ ┌─────────────────────────────┐ │ ┌───────────────────────┐ │
│ │ Rank Name  Pos College OVR │ │ │ QB - HIGH            │ │
│ │ 1    John  QB  Alabama  88 │ │ │ EDGE - MEDIUM        │ │
│ │ 2    Mike  WR  Georgia  87 │ │ │ CB - LOW             │ │
│ │ ...                         │ │ │ ...                  │ │
│ └─────────────────────────────┘ │ └───────────────────────┘ │
├─────────────────────────────────┴───────────────────────────┤
│ [Make Pick]  [Auto-Sim to My Next Pick]                     │
├─────────────────────────────────────────────────────────────┤
│ Pick History (Last 15 Picks)                                │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ Pick Round Team          Player        Pos           │   │
│ │ 1    1     Team Name     Player Name   QB            │   │
│ └───────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Prospects Table

- **Sortable Columns**: Click column headers to sort (numeric sorting for Rank, Overall, Potential)
- **Color Coding**:
  - Green: Elite prospects (85+ OVR)
  - Blue: High prospects (75-84 OVR)
  - Red: Low prospects (<65 OVR)
- **Selection**: Click a row to select, then click "Make Pick"

### Team Needs

- **Priority Color Coding**:
  - Red: Priority 1 (Critical need)
  - Yellow: Priority 2 (High need)
  - Gray: Priority 3+ (Moderate need)
- **Format**: `POSITION - URGENCY_LEVEL`

### Controls

#### Make Pick Button
- **Enabled**: Only when it's your turn
- **Action**: Draft the selected prospect
- **Behavior**: Automatically advances to next pick (CPU or user)

#### Auto-Sim Button
- **Enabled**: Always (until draft complete)
- **Action**: Simulates all picks until your next turn
- **Speed**: 500ms per pick (adjustable in code)

### Pick History

- Shows last 15 picks made
- Includes: Pick number, Round, Team name, Player name, Position
- Auto-scrolls as picks are made

## Usage Patterns

### Manual Picking

1. Wait for your turn (Make Pick button enabled)
2. Review available prospects table
3. Check your team needs
4. Select a prospect (click row)
5. Click "Make Pick"
6. Watch CPU teams make picks until your next turn

### Auto-Simulation

1. Click "Auto-Sim to My Next Pick"
2. Watch picks scroll by at 500ms intervals
3. Stops automatically when it's your turn
4. Make your selection

### Spectator Mode

1. Never click "Make Pick"
2. Use "Auto-Sim" repeatedly to watch entire draft
3. CPU teams will make all picks using AI logic

## AI Decision Making

CPU teams use simplified AI logic:

1. **Best Player Available (BPA)**: Rank prospects by overall + potential rating
2. **Team Need Multipliers**: Boost prospects at needed positions
3. **GM Personality**: Some GMs favor BPA, others favor need
4. **Priority Weighting**:
   - Priority 1 needs: Up to 1.5x multiplier
   - Priority 2 needs: Up to 1.3x multiplier
   - Priority 3 needs: Up to 1.15x multiplier

## Customization

### Change User Team

Edit `launch_dialog.py`:

```python
user_team_id = 19  # Philadelphia Eagles (see TeamIDs constants)
```

### Change Draft Year

Edit `launch_dialog.py`:

```python
season_year = 2027
```

### Adjust Auto-Sim Speed

Edit `draft_day_dialog.py` in `_auto_sim_next_pick()`:

```python
QTimer.singleShot(500, self._auto_sim_next_pick)  # Change 500 to desired milliseconds
```

### Adjust CPU Pick Delay

Edit `draft_day_dialog.py` in `advance_to_next_pick()`:

```python
QTimer.singleShot(1000, self.execute_cpu_pick)  # Change 1000 to desired milliseconds
```

## Integration with Main Application

To integrate this dialog into the main UI:

```python
from demo.draft_day_demo.draft_day_dialog import DraftDayDialog

# In your main window or controller
def launch_draft_day(self):
    dialog = DraftDayDialog(
        db_path=self.database_path,
        dynasty_id=self.current_dynasty_id,
        season=self.current_season,
        user_team_id=self.user_team_id,
        parent=self
    )
    dialog.exec()  # Modal dialog
    # or
    dialog.show()  # Non-modal dialog
```

## Known Limitations

1. **In-Memory Database**: `test_dialog.py` won't work properly (connection closes)
   - Use `launch_dialog.py` instead for full functionality

2. **Simplified AI**: Current AI just picks best available prospect
   - Real AI would consider positional value, draft strategy, etc.
   - See `draft_day_demo.py` for more sophisticated AI logic

3. **No Trade Support**: Dialog doesn't support draft pick trades
   - Would require additional UI for trade offers/acceptance

4. **No Pick Timer**: No countdown clock like real NFL draft
   - Could add QTimer-based countdown visualization

## Future Enhancements

Possible improvements:

- [ ] Draft pick trades dialog
- [ ] Countdown timer for each pick
- [ ] Prospect detail view on double-click
- [ ] Draft grade/analysis on completion
- [ ] Export draft results to file
- [ ] Save/load draft in progress
- [ ] Multiple draft board views (by position, by need, by grade)
- [ ] Live pick notifications/alerts
- [ ] War room notes/ratings for prospects

## Troubleshooting

### "Module not found" errors

Make sure you're running from the correct directory and have installed UI dependencies:

```bash
pip install -r requirements-ui.txt
cd demo/draft_day_demo
python launch_dialog.py
```

### Database connection errors

The dialog expects a file-based database. Use `launch_dialog.py` instead of `test_dialog.py`.

### Team names showing as "Team X"

This is normal - the dialog uses TeamIDs constants. Team names come from `team_loader.py`.

### UI not refreshing

Check console for errors. The dialog refreshes on every pick via `refresh_all_ui()`.

## See Also

- `draft_day_demo.py` - CLI version with more sophisticated AI
- `display_formatter.py` - ASCII art formatting for CLI version
- `ui/widgets/draft_prospects_widget.py` - Similar prospects table for main UI
- `ui/dialogs/prospect_detail_dialog.py` - Detailed prospect view dialog
