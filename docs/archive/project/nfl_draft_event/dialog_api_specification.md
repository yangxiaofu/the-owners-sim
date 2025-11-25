# Draft Day Dialog API Specification

**Created**: 2025-11-23
**Agent**: Dialog Migration Specialist (Phase 2)
**Source**: `demo/draft_day_demo/draft_day_dialog.py`
**Destination**: `ui/dialogs/draft_day_dialog.py`

## Overview

`DraftDayDialog` is a PySide6/Qt dialog providing an interactive UI for NFL draft simulation. It follows the Model-View-Controller pattern where the dialog acts as the View and delegates all business logic to a controller.

---

## Dialog Public API

### Constructor

```python
def __init__(
    self,
    controller: DraftDialogController,
    parent=None
)
```

**Parameters**:
- `controller` (DraftDialogController): Controller instance for business logic
- `parent` (QWidget, optional): Parent widget for Qt parenting

**Initializes**:
- Dialog window with 1000x700 size
- Window title: "Draft Day Simulation - {season} NFL Draft"
- Complete UI layout
- Initial UI refresh

---

### Public Methods

#### `refresh_all_ui()`
```python
def refresh_all_ui(self) -> None
```
Refreshes all UI components with current draft state.

**Behavior**:
- Updates current pick label with team and pick number
- Refreshes prospects table
- Refreshes team needs list
- Refreshes pick history
- Updates button enabled states based on user's turn
- Handles draft completion state

**Called By**:
- Constructor (initial refresh)
- `on_make_pick_clicked()` (after user pick)
- `execute_cpu_pick()` (after AI pick)
- `_auto_sim_next_pick()` (when stopping at user's turn)

---

#### `populate_prospects_table()`
```python
def populate_prospects_table(self) -> None
```
Populates the available prospects table with current draft class.

**Table Columns**:
1. Rank (int, sortable)
2. Name (string, stores player_id in UserRole)
3. Pos (string, centered)
4. College (string)
5. Overall (int, sortable, color-coded)

**Color Coding**:
- Green: Overall >= 85 (elite)
- Blue: Overall >= 75 (starter)
- Red: Overall < 65 (depth)
- Default: 65-74 (solid)

**Features**:
- Numeric sorting via `NumericTableWidgetItem`
- Stores player_id in name item's UserRole for selection
- Displays up to 300 prospects (configurable via controller)
- Default sort: ascending by rank

---

#### `populate_team_needs()`
```python
def populate_team_needs(self) -> None
```
Populates the team needs list with user team's position needs.

**Display Format**: `"QB - CRITICAL"`

**Color Coding**:
- Red: urgency_score >= 5 (CRITICAL)
- Yellow: urgency_score >= 3 (MODERATE/HIGH)
- Gray: urgency_score < 3 (LOW)

---

#### `populate_pick_history()`
```python
def populate_pick_history(self) -> None
```
Populates pick history table with last 15 executed picks.

**Table Columns**:
1. Pick (overall pick number)
2. Round (round number)
3. Team (full team name)
4. Player (first + last name)
5. Pos (position)

**Features**:
- Shows only completed picks (is_executed=True, player_id set)
- Limited to 15 most recent picks
- No sorting enabled

---

#### `advance_to_next_pick()`
```python
def advance_to_next_pick(self) -> None
```
Advances to next pick and determines if it's user's turn or CPU's turn.

**Behavior**:
- If user's turn: enables "Make Pick" button
- If CPU's turn: disables "Make Pick", schedules CPU pick after 1 second
- If draft complete: shows completion message

---

#### `execute_cpu_pick()`
```python
def execute_cpu_pick(self) -> None
```
Executes an AI-controlled draft pick.

**Behavior**:
- Calls `controller.execute_ai_pick()`
- Refreshes UI
- If next pick is also CPU (and not auto-simming), schedules next CPU pick after 1 second
- Handles exceptions gracefully with console logging

**Recursion**: Can chain CPU picks automatically when not in auto-sim mode

---

### Event Handlers

#### `on_make_pick_clicked()`
```python
def on_make_pick_clicked(self) -> None
```
Handler for "Make Pick" button click (user drafts selected prospect).

**Behavior**:
1. Validates selection (shows warning if no row selected)
2. Extracts player_id from selected row's UserRole data
3. Calls `controller.execute_user_pick(player_id)`
4. Refreshes UI
5. Advances to next pick
6. Shows error dialog on ValueError exceptions

---

#### `on_auto_sim_clicked()`
```python
def on_auto_sim_clicked(self) -> None
```
Handler for "Auto-Sim to My Next Pick" button click.

**Behavior**:
1. Disables both buttons during simulation
2. Starts recursive auto-simulation via `_auto_sim_next_pick()`
3. Simulation continues until user's turn or draft completion

---

### Private Methods

#### `_create_ui()`
```python
def _create_ui(self) -> None
```
Builds complete UI layout with 5 sections.

---

#### `_create_top_section()` → `QHBoxLayout`
Creates top info bar with current pick and user team labels.

---

#### `_create_middle_section()` → `QSplitter`
Creates middle section with prospects table (70%) and team needs (30%).

---

#### `_create_prospects_table()` → `QTableWidget`
Creates and configures prospects table widget.

---

#### `_create_team_needs_list()` → `QWidget`
Creates container with "Team Needs" label and list widget.

---

#### `_create_button_section()` → `QHBoxLayout`
Creates action buttons (Make Pick, Auto-Sim).

---

#### `_create_history_section()` → `QTableWidget`
Creates pick history table widget.

---

#### `_auto_sim_next_pick()`
```python
def _auto_sim_next_pick(self) -> None
```
Recursively simulates CPU picks until user's turn or draft completion.

**Recursion**: Schedules itself via QTimer.singleShot(500ms) for each CPU pick

---

#### `_show_draft_complete_message()`
```python
def _show_draft_complete_message(self) -> None
```
Shows completion message with pick count summary.

**Message Format**:
```
The {season} NFL Draft is complete!

Total picks made: {total}
Your picks: {user_count}

All prospects have been drafted.
```

---

## Required Controller API

The dialog expects the controller to implement the following interface:

### Controller Properties

```python
@property
def user_team_id(self) -> int
    """User's team ID (1-32)."""

@property
def season(self) -> int
    """Current draft season year."""

@property
def dynasty_id(self) -> str
    """Dynasty context identifier."""

@property
def draft_order(self) -> List[DraftPick]
    """Complete draft order (all 262 picks)."""

@property
def current_pick_index(self) -> int
    """Index of current pick in draft_order (0-261)."""

@property
def draft_api(self) -> DraftClassAPI
    """Direct access to draft database API."""
```

---

### Controller Methods

#### Data Retrieval

```python
def get_available_prospects(self, limit: int = 300) -> List[Dict[str, Any]]
    """
    Get list of undrafted prospects sorted by overall rating.

    Args:
        limit: Maximum number of prospects to return

    Returns:
        List of prospect dicts with keys:
            - player_id (int)
            - first_name (str)
            - last_name (str)
            - position (str)
            - college (str, optional)
            - overall (int)
    """
```

```python
def get_team_needs(self, team_id: int) -> List[Dict[str, Any]]
    """
    Get position needs for specified team.

    Args:
        team_id: Team ID (1-32)

    Returns:
        List of need dicts with keys:
            - position (str)
            - urgency (Enum or str)
            - urgency_score (int, 1-5)
    """
```

#### Draft Execution

```python
def execute_user_pick(self, player_id: int) -> Dict[str, Any]
    """
    Execute user's draft pick.

    Args:
        player_id: ID of prospect to draft

    Returns:
        Result dict with pick details

    Raises:
        ValueError: If pick is invalid (wrong team, already drafted, etc.)

    Side Effects:
        - Marks pick as executed in draft_order
        - Updates prospect's is_drafted flag
        - Increments current_pick_index
    """
```

```python
def execute_ai_pick(self) -> Dict[str, Any]
    """
    Execute AI-controlled draft pick for current team.

    Returns:
        Result dict with pick details

    Side Effects:
        - Selects best available prospect based on team needs
        - Marks pick as executed
        - Updates prospect's is_drafted flag
        - Increments current_pick_index
    """
```

#### State Queries

```python
def is_draft_complete(self) -> bool
    """
    Check if draft is complete (all picks executed).

    Returns:
        True if current_pick_index >= len(draft_order)
    """
```

---

## Signals

**Note**: The dialog does NOT emit any custom Qt signals. It communicates exclusively through controller method calls.

**No Signals Emitted**:
- All state changes handled via synchronous controller calls
- UI updates triggered by internal refresh methods
- No need for parent widgets to connect to dialog signals

---

## Qt Widget Dependencies

### PySide6 Imports

```python
from PySide6.QtWidgets import (
    QDialog,           # Base dialog class
    QVBoxLayout,       # Vertical layouts
    QHBoxLayout,       # Horizontal layouts
    QLabel,            # Text labels
    QTableWidget,      # Tables (prospects, history)
    QTableWidgetItem,  # Table cells
    QPushButton,       # Buttons
    QListWidget,       # Team needs list
    QSplitter,         # Resizable splitter
    QHeaderView,       # Table header configuration
    QMessageBox,       # Dialogs (warnings, info)
    QListWidgetItem,   # List items
    QWidget,           # Generic container
)
```

```python
from PySide6.QtCore import (
    Qt,      # Enums (AlignCenter, UserRole, etc.)
    QTimer,  # Delayed execution (CPU picks)
)
```

```python
from PySide6.QtGui import (
    QFont,   # Font styling
)
```

### Key Widgets

1. **QTableWidget** (prospects_table):
   - 5 columns, sortable, row selection
   - Alternating row colors
   - Custom `NumericTableWidgetItem` for numeric sorting
   - Stretch columns: Name, College

2. **QListWidget** (team_needs_list):
   - Color-coded items by urgency
   - Non-interactive (display only)

3. **QTableWidget** (pick_history_table):
   - 5 columns, non-sortable, read-only
   - Alternating row colors
   - Stretch columns: Team, Player

4. **QPushButton** (make_pick_btn, auto_sim_btn):
   - Custom stylesheets (blue, green)
   - Dynamic enable/disable based on turn

5. **QSplitter**:
   - Horizontal split (70% prospects, 30% needs)
   - Resizable by user

6. **QTimer**:
   - CPU pick delays (1000ms)
   - Auto-sim delays (500ms)

---

## Custom Classes

### `NumericTableWidgetItem`

```python
class NumericTableWidgetItem(QTableWidgetItem):
    """
    QTableWidgetItem that sorts numerically using UserRole data.

    Override of __lt__ to compare numeric values stored in Qt.UserRole
    instead of display text strings.
    """

    def __lt__(self, other: QTableWidgetItem) -> bool
        """Compare numerically using UserRole data."""
```

**Usage**:
- Rank column: stores int rank
- Overall column: stores int overall rating
- Pick number column: stores int pick number
- Round column: stores int round number

**Fallback**: If UserRole data is missing or non-numeric, falls back to string comparison.

---

## Integration Notes

### Controller Initialization Order

The dialog expects the controller to be fully initialized before construction:

1. Controller must have:
   - `draft_order` fully populated
   - `current_pick_index` set (usually 0)
   - `draft_api` connected to database
   - `user_team_id` and `dynasty_id` set

2. Dialog constructor calls `refresh_all_ui()` immediately
   - Expects controller to return valid data from all getters

### Error Handling

The dialog handles these error cases:

1. **No prospect selected**: Shows warning dialog
2. **Invalid player_id**: Shows warning dialog
3. **ValueError from execute_user_pick**: Shows error dialog with exception message
4. **Exception from execute_ai_pick**: Logs to console, continues

### Performance Considerations

1. **Table Population**: Disables sorting during population, re-enables after
2. **Auto-Sim Speed**: 500ms delays between CPU picks (configurable)
3. **CPU Pick Speed**: 1000ms delay before first CPU pick (configurable)
4. **Prospect Limit**: Default 300 prospects (prevents lag with large tables)

### UI Refresh Triggers

The dialog calls `refresh_all_ui()` after:
- Constructor (initial load)
- User makes pick
- AI makes pick
- Auto-sim stops at user's turn

**Optimization**: Consider adding dirty flags if refreshing all 3 tables becomes slow.

---

## Migration Changes from Demo

### Import Changes

**Removed**:
```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))
```

**Changed**:
```python
# Old (demo)
from draft_demo_controller import DraftDemoController

# New (production)
from ui.controllers.draft_controller import DraftDialogController  # TODO: Agent 4 will implement
```

### Controller Type

- Demo: `DraftDemoController`
- Production: `DraftDialogController` (to be implemented by Agent 4)

**Assumption**: Production controller will maintain same API as demo controller.

---

## Future Enhancements

Potential improvements for Phase 3+:

1. **Signals**: Add signals for parent widgets to track draft progress
   - `pick_executed(team_id: int, player_id: int, pick_number: int)`
   - `draft_completed()`
   - `user_pick_made(player_id: int)`

2. **Prospect Filtering**: Add position/rating filters to prospects table

3. **Trade Support**: Add "Trade Pick" button if trading is implemented

4. **Prospect Details**: Add double-click handler to show prospect details dialog

5. **Draft Board**: Add separate "Draft Board" view with big board rankings

6. **Pick Timer**: Add countdown timer for user picks (simulate real draft pressure)

7. **Multi-Selection**: Allow drafting multiple prospects in mock draft mode

---

## Testing Recommendations

1. **Unit Tests**:
   - Test `NumericTableWidgetItem` sorting with various data types
   - Test prospect table population with empty/large datasets
   - Test team needs display with various urgency levels

2. **Integration Tests**:
   - Test dialog with mock controller
   - Verify all controller methods called correctly
   - Test error handling with invalid controller responses

3. **UI Tests**:
   - Test button state transitions (enabled/disabled)
   - Test auto-sim stopping at correct pick
   - Test draft completion flow

4. **Edge Cases**:
   - Draft with no user picks
   - Draft where user has pick #1
   - Draft where user has consecutive picks
   - Empty draft class (should handle gracefully)

---

## Dependencies Summary

**Required Backend Components** (must exist before dialog can function):
- `DraftDialogController` (Agent 4 implementation)
- `DraftClassAPI` (database layer)
- `DraftPick` data model
- `TeamNeedsAnalyzer` (for get_team_needs)
- `team_management.teams.team_loader.get_team_by_id()`

**Qt Dependencies**:
- PySide6 6.0+ (installed via requirements-ui.txt)

**Python Version**:
- Python 3.13+ (for type hints and match/case if used)

---

## Summary

The `DraftDayDialog` is a fully-featured, production-ready UI component that:

- Follows MVC pattern with complete separation of concerns
- Provides rich interactive draft experience with user/AI picks
- Handles auto-simulation for non-interactive portions
- Uses proper Qt patterns (UserRole data, custom item classes, timers)
- Has comprehensive error handling
- Integrates cleanly with existing codebase via team_loader

**Controller Contract**: Agent 4 must implement `DraftDialogController` with the exact API documented in the "Required Controller API" section above.

**No Breaking Changes**: Dialog is a direct copy from demo with only import path updates. All logic preserved exactly as tested in demo environment.
