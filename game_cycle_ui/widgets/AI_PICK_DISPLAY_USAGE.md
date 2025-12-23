# AIPickDisplayWidget Usage Guide

## Overview

`AIPickDisplayWidget` is a rich display component for showing detailed draft pick information when AI teams make their selections. It provides a visually appealing ESPN-style card that shows:

- Team header with pick context
- Player information with photo placeholder
- Color-coded rating display
- Position needs addressed
- GM reasoning for the pick

## Import

```python
from game_cycle_ui.widgets import AIPickDisplayWidget
```

## Basic Usage

```python
# Create the widget
pick_display = AIPickDisplayWidget()

# Set pick data
pick_data = {
    "team_name": "Dallas Cowboys",
    "team_id": 17,
    "pick_number": 15,
    "round": 1,
    "pick_in_round": 15,
    "prospect_name": "Caleb Williams",
    "position": "QB",
    "college": "USC",
    "overall": 88,
    "needs_met": ["QB", "Leadership"],
    "reasoning": "Franchise quarterback with elite arm talent and mobility."
}

pick_display.set_pick_data(pick_data)

# Clear the display
pick_display.clear()

# Get current data
current_data = pick_display.get_current_data()
```

## Data Structure

### Required Fields

```python
{
    "team_name": str,        # e.g., "Dallas Cowboys"
    "team_id": int,          # 1-32 (from TeamIDs constants)
    "pick_number": int,      # Overall pick number (1-224)
    "round": int,            # Draft round (1-7)
    "pick_in_round": int,    # Pick number within round (1-32)
    "prospect_name": str,    # Player name
    "position": str,         # Position abbreviation (QB, WR, etc.)
    "college": str,          # College name
    "overall": int,          # Player rating (0-99)
    "needs_met": List[str],  # Positions this pick addresses
    "reasoning": str         # GM's draft reasoning
}
```

### Field Details

- **team_name**: Full team name as displayed in the header
- **team_id**: Numerical team ID (1-32, use `TeamIDs` constants)
- **pick_number**: Overall pick number with automatic ordinal suffix (1st, 2nd, 3rd, etc.)
- **round**: Current draft round (used for context)
- **pick_in_round**: Pick number within the round (used for context)
- **prospect_name**: Player's full name (automatically uppercase in display)
- **position**: Position abbreviation (displayed uppercase)
- **college**: College/university name
- **overall**: Player rating (0-99), color-coded based on thresholds:
  - 80+: Green (Elite)
  - 70-79: Blue (Solid)
  - 60-69: Orange (Project)
  - <60: Gray (Backup/Depth)
- **needs_met**: List of positions addressed (first = Critical, second = High, etc.)
- **reasoning**: Text explaining GM's decision (displayed in quotes, italic)

## Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│                     TEAM HEADER                             │
│        "With the 15th pick in the 2025 NFL Draft,          │
│              the Dallas Cowboys select..."                  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐                                                │
│  │  Photo  │   CALEB WILLIAMS                               │
│  │Placeholder  QB • USC                                    │
│  │         │                                                │
│  └─────────┘   Overall: 88 ████████░░ (green)              │
├─────────────────────────────────────────────────────────────┤
│  FILLS NEEDS AT: QB (Critical), Leadership (High)          │
├─────────────────────────────────────────────────────────────┤
│  GM REASONING:                                              │
│  "Franchise quarterback with elite arm talent and          │
│  mobility. Best player available aligns with needs."       │
└─────────────────────────────────────────────────────────────┘
```

## Integration Examples

### Draft View Integration

```python
from game_cycle_ui.widgets import AIPickDisplayWidget

class DraftView(QWidget):
    def __init__(self):
        super().__init__()

        # Create pick display widget
        self.ai_pick_display = AIPickDisplayWidget()
        self.ai_pick_display.hide()  # Hidden until AI picks

        # Add to layout
        layout.addWidget(self.ai_pick_display)

    def on_ai_team_pick(self, pick_result):
        """Handle AI team making a pick."""
        # Extract data from pick result
        pick_data = {
            "team_name": pick_result.get("team_name"),
            "team_id": pick_result.get("team_id"),
            "pick_number": pick_result.get("overall_pick"),
            "round": pick_result.get("round"),
            "pick_in_round": pick_result.get("pick_in_round"),
            "prospect_name": pick_result.get("prospect", {}).get("name"),
            "position": pick_result.get("prospect", {}).get("position"),
            "college": pick_result.get("prospect", {}).get("college"),
            "overall": pick_result.get("prospect", {}).get("overall"),
            "needs_met": pick_result.get("needs_addressed", []),
            "reasoning": pick_result.get("gm_reasoning", "")
        }

        # Show the pick
        self.ai_pick_display.set_pick_data(pick_data)

    def on_user_team_turn(self):
        """User's turn to pick - hide AI display."""
        self.ai_pick_display.clear()
```

### With Auto-Advance Timer

```python
from PySide6.QtCore import QTimer

class DraftController:
    def __init__(self):
        self.ai_pick_display = AIPickDisplayWidget()
        self.auto_advance_timer = QTimer()
        self.auto_advance_timer.timeout.connect(self.advance_to_next_pick)

    def process_ai_pick(self, pick_data):
        """Show AI pick for 3 seconds then auto-advance."""
        self.ai_pick_display.set_pick_data(pick_data)
        self.auto_advance_timer.start(3000)  # 3 second delay

    def advance_to_next_pick(self):
        """Move to next pick."""
        self.auto_advance_timer.stop()
        self.ai_pick_display.clear()
        # ... continue to next pick
```

## Styling

The widget automatically applies ESPN dark theme styling:

- **Card Background**: `#1a1a1a` (ESPN_THEME['card_bg'])
- **Border**: `#333333` (ESPN_THEME['border'])
- **Text Colors**: White primary, gray secondary/muted
- **Team Header**: Blue background (`Colors.INFO_DARK`)
- **Rating Colors**: Dynamic based on rating value

### Custom Styling

You can override styling if needed:

```python
pick_display = AIPickDisplayWidget()
pick_display.setStyleSheet("""
    AIPickDisplayWidget {
        background-color: #2a2a2a;
        border: 3px solid #1976D2;
    }
""")
```

## Methods

### `set_pick_data(pick_data: Dict[str, Any])`

Updates the display with new draft pick data. Automatically shows the widget.

**Args:**
- `pick_data`: Dictionary with all required pick information

**Example:**
```python
pick_display.set_pick_data({
    "team_name": "New England Patriots",
    "pick_number": 1,
    # ... other fields
})
```

### `clear()`

Clears all displayed data and hides the widget.

**Example:**
```python
pick_display.clear()
```

### `get_current_data() -> Optional[Dict[str, Any]]`

Returns the currently displayed pick data or `None` if no data is set.

**Returns:**
- `Dict[str, Any]`: Current pick data dictionary
- `None`: If widget has been cleared or no data set

**Example:**
```python
current = pick_display.get_current_data()
if current:
    print(f"Currently showing pick: {current['prospect_name']}")
```

## Demo Application

Run the demo to see the widget in action:

```bash
PYTHONPATH=src python demos/ai_pick_display_demo.py
```

The demo shows:
- Elite QB pick (88 OVR) - Green rating
- Solid WR pick (76 OVR) - Blue rating
- Developmental OL pick (64 OVR) - Orange rating
- Late round depth pick (52 OVR) - Gray rating

## Visual Indicators

### Rating Color Coding

Based on `RatingColorizer` thresholds:

| Rating Range | Color | Category | Meaning |
|--------------|-------|----------|---------|
| 80-99 | Green (#2E7D32) | Elite | Franchise potential |
| 70-79 | Blue (#1976D2) | Solid | Starter quality |
| 60-69 | Orange (#F57C00) | Project | Developmental upside |
| 0-59 | Gray (#666666) | Backup | Depth/special teams |

### Needs Priority Labels

Position needs are labeled by order in the list:

1. First position: **Critical**
2. Second position: **High**
3. Third position: **Moderate**
4. Fourth+ positions: **Low**

**Example:**
```python
"needs_met": ["QB", "WR", "Depth"]
# Displays: "QB (Critical), WR (High), Depth (Moderate)"
```

## Best Practices

1. **Always provide reasoning**: The GM reasoning text adds context and makes picks feel intentional
2. **Limit needs_met to 2-3 items**: Too many dilutes the message
3. **Clear between picks**: Always call `clear()` before showing the next pick
4. **Use actual team names**: Full team names read better than abbreviations in the header
5. **Show for 2-3 seconds**: Give users time to read before auto-advancing

## Accessibility

- All text uses high-contrast colors on dark backgrounds
- Font sizes follow Typography system (14px+ for readability)
- Word wrapping enabled for long text
- Clear visual hierarchy with section separators

## File Location

`/game_cycle_ui/widgets/ai_pick_display_widget.py`

## Dependencies

- PySide6 (Qt widgets)
- `game_cycle_ui.theme` (Colors, Typography, FontSizes, RatingColorizer)

## Related Components

- `PlayerSpotlightWidget` - Similar player card for media coverage
- `GMProposalCard` - Card-based display for GM proposals
- `DraftView` - Main draft interface (integration point)
