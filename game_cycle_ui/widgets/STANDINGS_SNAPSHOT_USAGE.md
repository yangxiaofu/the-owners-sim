# StandingsSnapshotWidget Usage Guide

## Overview

`StandingsSnapshotWidget` is a compact division standings viewer with a dropdown selector. Perfect for dashboard sidebars or overview screens where space is limited (~200px height).

## Features

- **Division Dropdown**: Select any of 8 NFL divisions (AFC/NFC East/North/South/West)
- **Compact Display**: Shows 4 teams per division with W-L records
- **Playoff Indicators**: 🟢 (in playoff position) or 🔴 (out of playoffs)
- **Clickable Teams**: Navigate to team details by clicking rows
- **Auto-Default**: Can default to user's team division
- **Fixed Height**: ~200px total (header + dropdown + 4 team rows)

## Quick Start

```python
from game_cycle_ui.widgets import StandingsSnapshotWidget

# Create widget
standings_widget = StandingsSnapshotWidget()

# Set context (optional - for future database integration)
standings_widget.set_context(
    dynasty_id="dynasty_001",
    db_path="data/database/game_cycle/game_cycle.db",
    user_team_id=22  # Detroit Lions
)

# Connect signals
standings_widget.team_clicked.connect(on_team_selected)
standings_widget.division_changed.connect(on_division_changed)

# Add to layout
sidebar_layout.addWidget(standings_widget)
```

## API Reference

### Initialization

```python
widget = StandingsSnapshotWidget(parent=None)
```

Creates the widget with placeholder data (8 divisions, realistic standings).

### Methods

#### `set_context(dynasty_id: str, db_path: str, user_team_id: int)`

Set the widget context for database integration (future use).

**Parameters:**
- `dynasty_id`: Dynasty identifier
- `db_path`: Path to game_cycle.db
- `user_team_id`: User's team ID (1-32, determines default division)

**Example:**
```python
widget.set_context("dynasty_001", "data/database/game_cycle/game_cycle.db", 22)
```

---

#### `set_division(division_name: str)`

Programmatically change the selected division.

**Parameters:**
- `division_name`: Division name (e.g., "AFC East", "NFC North")

**Valid Values:**
- `"AFC East"`, `"AFC North"`, `"AFC South"`, `"AFC West"`
- `"NFC East"`, `"NFC North"`, `"NFC South"`, `"NFC West"`

**Example:**
```python
widget.set_division("NFC North")  # Show Lions, Vikings, Packers, Bears
```

---

#### `set_standings(standings_data: List[Dict])`

Update the standings data and refresh the display.

**Parameters:**
- `standings_data`: List of team standings dictionaries

**Required Dict Keys:**
- `team_id` (int): Team ID (1-32)
- `team_abbrev` (str): Team abbreviation (e.g., "BUF", "MIA")
- `conference` (str): "AFC" or "NFC"
- `division` (str): "East", "North", "South", or "West"
- `wins` (int): Number of wins
- `losses` (int): Number of losses
- `ties` (int): Number of ties (optional, default 0)

**Optional Dict Keys:**
- `playoff_seed` (int): Playoff seed 1-7 (if in playoffs)
- `division_rank` (int): Rank within division 1-4 (auto-calculated if missing)
- `in_playoff_position` (bool): True if in playoff position (auto-calculated if missing)

**Example:**
```python
standings = [
    {
        "team_id": 1,
        "team_abbrev": "BUF",
        "conference": "AFC",
        "division": "East",
        "wins": 10,
        "losses": 3,
        "ties": 0,
        "playoff_seed": 2,
        "division_rank": 1
    },
    {
        "team_id": 2,
        "team_abbrev": "MIA",
        "conference": "AFC",
        "division": "East",
        "wins": 8,
        "losses": 5,
        "ties": 0,
        "division_rank": 2
    },
    # ... more teams
]

widget.set_standings(standings)
```

---

#### `clear()`

Clear all standings data and remove team rows.

**Example:**
```python
widget.clear()
```

---

### Signals

#### `team_clicked(team_id: int)`

Emitted when a team row is clicked.

**Parameters:**
- `team_id`: The clicked team's ID (1-32)

**Example:**
```python
@Slot(int)
def on_team_clicked(team_id):
    print(f"Team {team_id} clicked - navigate to team view")
    # Navigate to team detail page, etc.

widget.team_clicked.connect(on_team_clicked)
```

---

#### `division_changed(division_name: str)`

Emitted when the dropdown selection changes.

**Parameters:**
- `division_name`: The new division name (e.g., "AFC East")

**Example:**
```python
@Slot(str)
def on_division_changed(division_name):
    print(f"Now showing: {division_name}")
    # Update related widgets, save preference, etc.

widget.division_changed.connect(on_division_changed)
```

---

## Integration Examples

### Example 1: Dashboard Sidebar

```python
from PySide6.QtWidgets import QVBoxLayout, QWidget
from game_cycle_ui.widgets import StandingsSnapshotWidget

class DashboardSidebar(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # Add standings widget
        self.standings = StandingsSnapshotWidget()
        self.standings.set_division("AFC North")  # Default to user's division
        self.standings.team_clicked.connect(self.navigate_to_team)

        layout.addWidget(self.standings)
        layout.addStretch()

    def navigate_to_team(self, team_id: int):
        """Navigate to team detail view."""
        # Emit signal to main window, switch view, etc.
        pass
```

### Example 2: Live Data from Database

```python
import sqlite3
from game_cycle_ui.widgets import StandingsSnapshotWidget

def load_standings_from_db(widget: StandingsSnapshotWidget, dynasty_id: str):
    """Load current standings from game_cycle.db."""
    conn = sqlite3.connect("data/database/game_cycle/game_cycle.db")
    conn.row_factory = sqlite3.Row

    query = """
        SELECT
            team_id,
            team_abbrev,
            conference,
            division,
            wins,
            losses,
            ties,
            playoff_seed,
            division_rank
        FROM standings
        WHERE dynasty_id = ? AND season = ?
        ORDER BY conference, division, division_rank
    """

    cursor = conn.execute(query, (dynasty_id, 2024))
    rows = cursor.fetchall()

    standings_data = [dict(row) for row in rows]
    widget.set_standings(standings_data)

    conn.close()
```

### Example 3: Reactive Updates

```python
from PySide6.QtCore import QTimer
from game_cycle_ui.widgets import StandingsSnapshotWidget

class LiveStandingsWidget(StandingsSnapshotWidget):
    """Auto-refreshing standings widget."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Refresh every 30 seconds during games
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_standings)
        self.timer.start(30000)  # 30 seconds

    def refresh_standings(self):
        """Reload standings from database."""
        # Fetch latest data and update
        standings = fetch_standings_from_api()
        self.set_standings(standings)
```

---

## Styling

The widget uses the ESPN dark theme defined in `game_cycle_ui/theme.py`:

- **Background**: `#0d0d0d` (ESPN_DARK_BG)
- **Card Background**: `#1a1a1a` (ESPN_CARD_BG)
- **Header Accent**: `#cc0000` (ESPN_RED)
- **Text Primary**: `#FFFFFF` (white)
- **Text Secondary**: `#888888` (gray)
- **Playoff Green**: 🟢
- **Out of Playoffs Red**: 🔴

The dropdown has custom dark styling with:
- Dark background (#2a2a2a)
- Red border on hover
- Custom arrow indicator
- Dark dropdown menu

---

## Layout Specifications

**Total Height**: ~200px
- Header: ~60px (title + dropdown)
- Team Rows: 4 × 28px = ~112px
- Spacing/Padding: ~28px

**Recommended Usage:**
- Sidebar widgets (200-300px wide)
- Dashboard panels
- Quick-glance overview screens

**Not Recommended:**
- Full standings page (use `StandingsTableWidget` instead)
- Mobile layouts (too compact)

---

## Testing

Run the included test script:

```bash
PYTHONPATH=src python test_standings_snapshot.py
```

This launches a test window demonstrating:
- Division dropdown functionality
- Team row clicks
- Division change signals
- Playoff indicators
- All 8 divisions with realistic data

---

## Future Enhancements

The following features are placeholders for future implementation:

1. **Database Integration**: `set_context()` method ready for database queries
2. **User Team Default**: Auto-select user's division on initialization
3. **Live Updates**: WebSocket/signal-based real-time standings updates
4. **Seed Highlighting**: Color-code teams by playoff seed (1-7)
5. **Hover Tooltips**: Show full team name, record details on hover
6. **Click Actions**: Configurable click behavior (navigate, popup, etc.)

---

## Common Issues

### Issue: Dropdown not showing all divisions
**Solution**: Ensure `DIVISION_OPTIONS` has all 8 divisions and dropdown is wide enough.

### Issue: Playoff indicators wrong
**Solution**: Verify `playoff_seed` or `in_playoff_position` in standings data.

### Issue: Teams not sorting correctly
**Solution**: Check `division_rank` is provided or verify wins/losses for auto-sort.

### Issue: Widget height too large
**Solution**: Widget is fixed at 200px. Check parent layout isn't forcing expansion.

---

## See Also

- `StandingsTableWidget`: Full conference standings with 4 division tables
- `PowerRankingsWidget`: Two-column power rankings (1-32)
- `PlayoffPictureWidget`: Playoff bracket visualization
- `theme.py`: ESPN dark theme constants
