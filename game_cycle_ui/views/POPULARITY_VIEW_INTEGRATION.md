# PopularityView Integration Guide

## Overview

The **PopularityView** widget displays league-wide player popularity rankings, showing the top 50 most popular players with detailed metrics and filtering capabilities.

## Features

- **Sortable Table**: Click column headers to sort by any metric
- **Tier Filtering**: Filter by popularity tier (Transcendent, Star, Known, Role Player, Unknown)
- **Position Filtering**: Filter by position (QB, RB, WR, TE, EDGE, DT, LB, CB, S, K, P)
- **Trend Indicators**: Visual arrows (↑/↓/→) with week-over-week change
- **Component Breakdown**: Shows Performance, Visibility, and Market multipliers
- **Player Details**: Double-click any player to open PlayerDetailDialog
- **Refresh**: Recalculate current week's popularity on demand

## Integration with Main Window

### Step 1: Import the View

```python
from game_cycle_ui.views import PopularityView
```

### Step 2: Create the View Instance

In your main window's `__init__`:

```python
self.popularity_view = PopularityView()
```

### Step 3: Add to Navigation

Add a new tab to your main navigation (e.g., alongside "Team", "League", "Schedule"):

```python
self.main_tabs.addTab(self.popularity_view, "Popularity")
```

### Step 4: Set Context

When setting up dynasty context (typically after loading a save game):

```python
self.popularity_view.set_context(
    dynasty_id=self.dynasty_id,
    db_path=self.db_path,  # Path to game_cycle.db
    season=self.current_season,
    week=self.current_week
)
```

### Step 5: Refresh Data

Call `refresh_rankings()` whenever you need to update the display:

```python
# After advancing week
self.popularity_view.refresh_rankings()

# Or connect to a signal
self.stage_controller.week_advanced.connect(
    self.popularity_view.refresh_rankings
)
```

## Example Integration

```python
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Create main tabs
        self.main_tabs = QTabWidget()

        # Create popularity view
        self.popularity_view = PopularityView()
        self.main_tabs.addTab(self.popularity_view, "Popularity")

        # Connect refresh signal
        self.popularity_view.refresh_requested.connect(
            self._on_popularity_refresh
        )

    def load_dynasty(self, dynasty_id, db_path, season, week):
        """Load dynasty and set context for all views."""
        self.popularity_view.set_context(
            dynasty_id=dynasty_id,
            db_path=db_path,
            season=season,
            week=week
        )
        self.popularity_view.refresh_rankings()

    def _on_popularity_refresh(self):
        """Handle popularity view refresh request."""
        # Optionally trigger recalculation from popularity service
        # or just refresh the display
        self.popularity_view.refresh_rankings()
```

## Database Requirements

The PopularityView requires:

1. **game_cycle.db** with `player_popularity` table (popularity scores)
2. **nfl_simulation.db** with `players` table (player names, positions, teams)

The view handles cross-database queries internally to fetch player metadata.

## Styling

The view uses the standard ESPN dark theme from `game_cycle_ui/theme.py`:

- **Tier Colors**:
  - Transcendent (90-100): Gold (#FFD700)
  - Star (75-89): Silver (#C0C0C0)
  - Known (50-74): Green (#4CAF50)
  - Role Player (25-49): Blue (#1976D2)
  - Unknown (0-24): Gray (#666666)

- **Trend Colors**:
  - Rising: Green (#2E7D32)
  - Falling: Red (#C62828)
  - Stable: Gray (#666666)

## Testing

Run the demo:
```bash
python demos/popularity_view_demo.py
```

Run tests:
```bash
python -m pytest tests/game_cycle_ui/test_popularity_view.py -v
```

## API Reference

### Constructor

```python
PopularityView(parent: Optional[QWidget] = None)
```

### Methods

#### `set_context(dynasty_id: str, db_path: str, season: int, week: int)`
Set dynasty context for data queries.

#### `refresh_rankings()`
Refresh popularity rankings from database.

#### `clear()`
Clear all data from the view.

### Signals

#### `refresh_requested`
Emitted when user clicks the Refresh button.

## Notes

- **Performance**: Fetching top 50 players is fast (< 100ms)
- **Cross-Database**: View handles queries across game_cycle.db and nfl_simulation.db
- **Filtering**: Tier and position filters work together (AND logic)
- **Sorting**: All columns support sorting via NumericTableWidgetItem
- **Player Detail**: Double-click opens full player detail dialog with stats history

## Future Enhancements

Potential future additions:

1. **Sparklines**: 4-week trend mini-charts for each player
2. **Export**: CSV/PDF export of rankings
3. **Team Summary**: Team-level popularity aggregation
4. **Historical View**: Compare popularity across multiple weeks/seasons
5. **Search**: Quick player name search/filter
