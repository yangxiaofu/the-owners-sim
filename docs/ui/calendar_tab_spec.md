# Calendar Tab UI Specification

**Version:** 1.0.0
**Last Updated:** 2025-10-04
**Status:** Specification - Ready for Implementation
**Target Phase:** Phase 2-3 (After Season/Team views)

---

## Table of Contents

1. [Overview](#overview)
2. [Purpose & Goals](#purpose--goals)
3. [Data Sources & Integration](#data-sources--integration)
4. [UI Layout & Components](#ui-layout--components)
5. [Technical Architecture](#technical-architecture)
6. [Event Display Specifications](#event-display-specifications)
7. [User Interactions](#user-interactions)
8. [Visual Design](#visual-design)
9. [Implementation Plan](#implementation-plan)
10. [Integration Points](#integration-points)

---

## Overview

The **Calendar Tab** provides a comprehensive month-by-month view of all NFL season events, spanning the entire football year from September (season start) through August (training camp/preseason). Users can navigate backward and forward through months to see games, offseason deadlines, free agency windows, and league milestones.

### Key Features

- **Month navigation**: Forward/backward buttons to browse NFL calendar
- **Event type filtering**: Toggle visibility of games, deadlines, windows, milestones
- **Event details**: Click any event to see full information
- **Color-coded events**: Visual distinction between event types
- **"Jump to today"**: Quick navigation to current date
- **Dynasty-aware**: Shows only events for active dynasty

---

## Purpose & Goals

### Primary Goals

1. **Provide calendar context**: Users understand where they are in the NFL year
2. **Surface upcoming events**: See what's coming next (games, deadlines)
3. **Track offseason timeline**: Visualize complex 7-month offseason with all deadlines
4. **Enable planning**: Users can plan franchise tag decisions, free agency, draft prep
5. **Historical view**: Review past games and deadline compliance

### User Stories

- *"As a user, I want to see all games scheduled for November so I can plan simulations"*
- *"As a user, I want to see when the franchise tag deadline is so I don't miss it"*
- *"As a user, I want to filter out games and only see offseason deadlines"*
- *"As a user, I want to click on a game to see its details or box score"*
- *"As a user, I want to jump to today's date quickly"*

---

## Data Sources & Integration

### Event Database (`src/events/event_database_api.py`)

The calendar retrieves all events from the unified events database:

```python
# EventDatabaseAPI methods used:
- get_events_in_date_range(start_date, end_date, dynasty_id)
- get_events_by_type(event_type, dynasty_id)
- get_event_by_id(event_id)
```

### Event Types Displayed

| Event Type | Source File | Purpose | Display Priority |
|------------|-------------|---------|------------------|
| **GAME** | `game_event.py` | NFL regular season/playoff games | HIGH |
| **DEADLINE** | `deadline_event.py` | Offseason deadlines (franchise tag, RFA, roster cuts) | HIGH |
| **WINDOW** | `window_event.py` | Time windows (legal tampering, free agency, OTAs) | MEDIUM |
| **MILESTONE** | `milestone_event.py` | Informational markers (Super Bowl, Combine, schedule release) | LOW |

### Event Data Structure

Each event provides:
- `event_id`: Unique identifier
- `event_type`: Type classification
- `timestamp`: Date/time of event
- `data`: Event-specific information (teams, description, results, etc.)
- `game_id`: Grouping identifier

---

## UI Layout & Components

### Main Layout (Two-Panel Design)

```
┌─────────────────────────────────────────────────────────────────┐
│ Calendar Tab                                     Dynasty: Eagles │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Calendar Navigation Panel                                   │ │
│ │ ┌─────┐  ┌──────────────────┐  ┌─────┐  ┌──────────────┐  │ │
│ │ │ <<  │  │  November 2024   │  │ >>  │  │ Jump to Today│  │ │
│ │ └─────┘  └──────────────────┘  └─────┘  └──────────────┘  │ │
│ │                                                             │ │
│ │ Filters: [✓] Games  [✓] Deadlines  [✓] Windows  [✓] Milestones │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Calendar Grid / Event List                                  │ │
│ │ ┌────────────────────────────────────────────────────────┐  │ │
│ │ │ Sun  Mon  Tue  Wed  Thu  Fri  Sat                      │  │ │
│ │ ├────────────────────────────────────────────────────────┤  │ │
│ │ │      1    2    3    4    5    6    7                   │  │ │
│ │ │          [G]  [G]  [D]       [G]                       │  │ │
│ │ │  8    9   10   11   12   13   14                       │  │ │
│ │ │     [G]  [G]  [G]       [G]  [G]                       │  │ │
│ │ │ 15   16   17   18   19   20   21                       │  │ │
│ │ │     [M]  [G]  [G]       [G]  [G]                       │  │ │
│ │ │ ... (rest of month)                                    │  │ │
│ │ └────────────────────────────────────────────────────────┘  │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Event Details Panel (Selected Event)                        │ │
│ │ ┌─────────────────────────────────────────────────────────┐ │ │
│ │ │ Nov 10, 2024 - NFL Game                                 │ │ │
│ │ │ Philadelphia Eagles @ Dallas Cowboys                    │ │ │
│ │ │ 8:15 PM ET | Week 10                                   │ │ │
│ │ │ Status: Completed                                       │ │ │
│ │ │ Score: Eagles 24, Cowboys 17                           │ │ │
│ │ │ [View Box Score] [View Game Log]                       │ │ │
│ │ └─────────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Alternative: List View (More OOTP-like)

```
┌─────────────────────────────────────────────────────────────────┐
│ Event List for November 2024                                     │
├──────┬───────────┬──────────────────────┬──────────────────────┤
│ Date │ Type      │ Event                │ Status/Details       │
├──────┼───────────┼──────────────────────┼──────────────────────┤
│ 11/1 │ GAME      │ Eagles @ Giants      │ Completed: 28-14     │
│ 11/2 │ GAME      │ Cowboys vs Browns    │ Completed: 21-17     │
│ 11/4 │ DEADLINE  │ Waiver Priority Res  │ Passed               │
│ 11/6 │ GAME      │ Eagles @ Commanders  │ Scheduled            │
│ 11/8 │ GAME      │ Cowboys @ Eagles     │ Scheduled            │
│ 11/10│ MILESTONE │ Schedule Release     │ Info                 │
│ ...  │ ...       │ ...                  │ ...                  │
└──────┴───────────┴──────────────────────┴──────────────────────┘
```

**Recommendation**: Start with **List View** for Phase 2 (easier to implement), add **Grid View** in Phase 3.

### Component Breakdown

#### 1. Calendar Header
- **Previous Month Button** (`<<`): Navigate to previous month
- **Current Month/Year Display**: Large, centered text (e.g., "November 2024")
- **Next Month Button** (`>>`): Navigate to next month
- **Jump to Today Button**: Quick navigation to current date

#### 2. Filter Controls
- **Checkboxes** for each event type:
  - `[✓] Games` - Show/hide NFL games
  - `[✓] Deadlines` - Show/hide offseason deadlines
  - `[✓] Windows` - Show/hide time windows
  - `[✓] Milestones` - Show/hide informational milestones
- State persisted across sessions

#### 3. Event List/Grid
- **List View** (Phase 2):
  - QTableView with 4 columns: Date | Type | Event | Status
  - Sortable by date
  - Color-coded rows by event type
  - Single-click selection

- **Grid View** (Phase 3):
  - Traditional calendar grid (7 columns = days of week)
  - Each cell shows date + event indicators
  - Event indicators: `[G]` = Game, `[D]` = Deadline, `[W]` = Window, `[M]` = Milestone
  - Hover shows tooltip with event summary

#### 4. Event Details Panel
- **Header**: Event type + date
- **Game Events**:
  - Team names (away @ home)
  - Week number
  - Status: Scheduled | In Progress | Completed
  - Score (if completed)
  - Buttons: [View Box Score] [View Play-by-Play]

- **Deadline Events**:
  - Deadline type (e.g., "Franchise Tag Deadline")
  - Description
  - Compliance status (if applicable)
  - Action button: [View Compliance Report]

- **Window Events**:
  - Window name (e.g., "Legal Tampering Period")
  - Start/End marker
  - Description
  - Active status

- **Milestone Events**:
  - Milestone type (e.g., "NFL Combine")
  - Description
  - Additional context/metadata

---

## Technical Architecture

### Component Structure

```
ui/views/calendar_view.py
├── CalendarView (QWidget)
│   ├── Header (QHBoxLayout)
│   │   ├── PrevMonthButton (QPushButton)
│   │   ├── MonthYearLabel (QLabel)
│   │   ├── NextMonthButton (QPushButton)
│   │   └── JumpTodayButton (QPushButton)
│   │
│   ├── Filters (QHBoxLayout)
│   │   ├── GamesCheckbox (QCheckBox)
│   │   ├── DeadlinesCheckbox (QCheckBox)
│   │   ├── WindowsCheckbox (QCheckBox)
│   │   └── MilestonesCheckbox (QCheckBox)
│   │
│   ├── EventListTable (QTableView)
│   │   └── CalendarModel (QAbstractTableModel)
│   │
│   └── EventDetailsPanel (QWidget)
│       └── EventDetailsLayout (QVBoxLayout)
```

### Controller: `ui/controllers/calendar_controller.py`

```python
class CalendarController:
    """
    Controller for Calendar view operations.

    Mediates between CalendarView and event database.
    """

    def __init__(self, db_path: str, dynasty_id: str):
        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self.event_api = EventDatabaseAPI(db_path)
        self.current_month = datetime.now().month
        self.current_year = datetime.now().year

    def get_events_for_month(self, year: int, month: int,
                             event_types: List[str]) -> List[Dict]:
        """Get all events in specified month filtered by type."""
        start_date = datetime(year, month, 1)

        # Last day of month
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)

        # Get all events in range
        all_events = self.event_api.get_events_in_date_range(
            start_date=start_date,
            end_date=end_date,
            dynasty_id=self.dynasty_id
        )

        # Filter by event type
        filtered = [e for e in all_events if e['event_type'] in event_types]

        # Sort by date
        filtered.sort(key=lambda e: e['timestamp'])

        return filtered

    def navigate_month(self, direction: int):
        """Navigate months (direction: -1 = prev, +1 = next)."""
        self.current_month += direction

        if self.current_month > 12:
            self.current_month = 1
            self.current_year += 1
        elif self.current_month < 1:
            self.current_month = 12
            self.current_year -= 1

    def jump_to_today(self):
        """Reset to current month/year."""
        now = datetime.now()
        self.current_month = now.month
        self.current_year = now.year

    def get_event_details(self, event_id: str) -> Dict:
        """Get full event details by ID."""
        return self.event_api.get_event_by_id(event_id, self.dynasty_id)
```

### Model: `ui/models/calendar_model.py`

```python
class CalendarModel(QAbstractTableModel):
    """
    Qt table model for calendar events.

    Displays events in list format with 4 columns:
    - Date
    - Type
    - Event (description)
    - Status
    """

    COL_DATE = 0
    COL_TYPE = 1
    COL_EVENT = 2
    COL_STATUS = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self._events = []
        self._headers = ["Date", "Type", "Event", "Status"]

    def set_events(self, events: List[Dict]):
        """Update model with new event data."""
        self.beginResetModel()
        self._events = events
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._events)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 4

    def data(self, index: QModelIndex, role: int):
        """Return data for display."""
        if not index.isValid():
            return None

        event = self._events[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == self.COL_DATE:
                dt = datetime.fromisoformat(event['timestamp'])
                return dt.strftime("%m/%d")

            elif col == self.COL_TYPE:
                return event['event_type']

            elif col == self.COL_EVENT:
                return self._format_event_description(event)

            elif col == self.COL_STATUS:
                return self._format_event_status(event)

        elif role == Qt.BackgroundRole:
            # Color-code by event type
            event_type = event['event_type']
            if event_type == 'GAME':
                return QColor(200, 230, 255)  # Light blue
            elif event_type == 'DEADLINE':
                return QColor(255, 200, 200)  # Light red
            elif event_type == 'WINDOW':
                return QColor(255, 255, 200)  # Light yellow
            elif event_type == 'MILESTONE':
                return QColor(220, 255, 220)  # Light green

        return None

    def _format_event_description(self, event: Dict) -> str:
        """Format event description based on type."""
        event_type = event['event_type']
        data = event['data']

        if event_type == 'GAME':
            params = data.get('parameters', data)
            away = params.get('away_team_id', '?')
            home = params.get('home_team_id', '?')
            return f"Team {away} @ Team {home}"

        elif event_type == 'DEADLINE':
            params = data.get('parameters', data)
            return params.get('description', 'Deadline')

        elif event_type == 'WINDOW':
            params = data.get('parameters', data)
            name = params.get('window_name', '')
            wtype = params.get('window_type', '')
            return f"{name} {wtype}"

        elif event_type == 'MILESTONE':
            params = data.get('parameters', data)
            return params.get('description', 'Milestone')

        return "Unknown Event"

    def _format_event_status(self, event: Dict) -> str:
        """Format event status based on results."""
        data = event['data']
        results = data.get('results')

        if results:
            # Event has been executed
            if event['event_type'] == 'GAME':
                away_score = results.get('away_score', 0)
                home_score = results.get('home_score', 0)
                return f"{away_score}-{home_score}"
            else:
                return "Completed"
        else:
            # Event not yet executed
            return "Scheduled"
```

---

## Event Display Specifications

### Event Type: GAME

**List View Format:**
```
Date   | Type  | Event                      | Status
11/10  | GAME  | Eagles @ Cowboys (Week 10) | 24-17
```

**Details Panel:**
```
Nov 10, 2024 - NFL Game
Philadelphia Eagles @ Dallas Cowboys
8:15 PM ET | Week 10 | Regular Season
Status: Completed
Final Score: Eagles 24, Cowboys 17

[View Box Score] [View Play-by-Play]
```

**Color**: Light blue background (`#C8E6FF`)

---

### Event Type: DEADLINE

**List View Format:**
```
Date   | Type     | Event                      | Status
03/04  | DEADLINE | Franchise Tag Deadline     | Passed
```

**Details Panel:**
```
Mar 4, 2025 - Franchise Tag Deadline
4:00 PM ET

Teams must designate all franchise and transition tag players
by this date. Tags become official at 4PM ET.

Compliance Status: 32/32 teams compliant
[View Tag Summary]
```

**Color**: Light red background (`#FFC8C8`)

**Deadline Types Displayed:**
- Franchise Tag Deadline (early March)
- RFA Tender Deadline (mid-March)
- Salary Cap Compliance (mid-March)
- Draft Declaration Deadline (January)
- Rookie Contract Signing (May-July)
- Final Roster Cuts (late August)

---

### Event Type: WINDOW

**List View Format:**
```
Date   | Type   | Event                       | Status
03/10  | WINDOW | Legal Tampering START       | Active
03/12  | WINDOW | Legal Tampering END         | Closed
```

**Details Panel:**
```
Mar 10, 2025 - Legal Tampering Period STARTS
12:00 PM ET

Teams may negotiate with pending free agents from other teams.
No contracts can be signed until Free Agency officially opens.

Duration: Mar 10 (Noon) - Mar 12 (4PM)
Status: Currently Active
```

**Color**: Light yellow background (`#FFFFC8`)

**Window Types Displayed:**
- Legal Tampering Period
- Free Agency Period
- OTA/Minicamp Windows
- Training Camp
- Roster Reduction Period

---

### Event Type: MILESTONE

**List View Format:**
```
Date   | Type      | Event                  | Status
02/02  | MILESTONE | Super Bowl LIX         | Info
```

**Details Panel:**
```
Feb 2, 2025 - Super Bowl LIX
Allegiant Stadium, Las Vegas, NV
6:30 PM ET

Championship game of the 2024-2025 NFL season.

Winner: TBD
MVP: TBD
```

**Color**: Light green background (`#DCFFDC`)

**Milestone Types Displayed:**
- Super Bowl
- Pro Bowl
- NFL Combine
- League Meetings
- Schedule Release
- Hall of Fame Induction

---

## User Interactions

### Navigation Controls

| Action | Control | Behavior |
|--------|---------|----------|
| **Previous Month** | `<<` Button | Navigate to previous month, reload events |
| **Next Month** | `>>` Button | Navigate to next month, reload events |
| **Jump to Today** | "Jump to Today" Button | Reset to current month/year |
| **Select Event** | Click row in table | Load event details in panel below |
| **Filter Events** | Checkboxes | Show/hide event types, refresh display |

### Keyboard Shortcuts

- `Left Arrow`: Previous month
- `Right Arrow`: Next month
- `Home`: Jump to today
- `Up/Down Arrows`: Navigate event list

### Event Actions

**From Details Panel:**

- **Games**:
  - `[View Box Score]` → Navigate to Game tab with box score
  - `[View Play-by-Play]` → Navigate to Game tab with play log

- **Deadlines**:
  - `[View Compliance]` → Show compliance report modal
  - `[View Teams]` → List teams affected by deadline

- **Windows**:
  - `[View Activity]` → Show transactions during window

- **Milestones**:
  - `[Learn More]` → Show additional context/information

---

## Visual Design

### Color Scheme (OOTP-Inspired)

| Event Type | Background | Text | Border |
|------------|-----------|------|--------|
| GAME | `#C8E6FF` (Light Blue) | `#003366` (Dark Blue) | `#0066CC` |
| DEADLINE | `#FFC8C8` (Light Red) | `#660000` (Dark Red) | `#CC0000` |
| WINDOW | `#FFFFC8` (Light Yellow) | `#666600` (Dark Yellow) | `#CCCC00` |
| MILESTONE | `#DCFFDC` (Light Green) | `#006600` (Dark Green) | `#00CC00` |

### Typography

- **Month/Year Header**: 24px bold
- **Event List**: 12px regular
- **Event Details Title**: 18px bold
- **Event Details Body**: 14px regular

### Spacing

- **Panel Margins**: 20px
- **Widget Spacing**: 15px
- **Table Row Height**: 32px
- **Button Padding**: 8px 16px

---

## Implementation Plan

### Phase 2: Basic Calendar (List View)

**Week 1-2:**
1. Create `CalendarController` with month navigation
2. Create `CalendarModel` for event list
3. Create `CalendarView` with list table
4. Wire navigation buttons (prev/next/today)
5. Basic event filtering (checkboxes)

**Deliverable**: Functional calendar list showing all events for selected month

---

### Phase 3: Enhanced Calendar (Grid View + Details)

**Week 3-4:**
1. Add event details panel
2. Implement event selection and detail loading
3. Create traditional calendar grid widget
4. Add view toggle (list ↔ grid)
5. Implement event action buttons

**Deliverable**: Full-featured calendar with grid view and event interactions

---

### Phase 4: Advanced Features

**Week 5-6:**
1. Add date range filter (custom date picker)
2. Implement event search functionality
3. Add "upcoming events" widget
4. Calendar export (PDF/CSV)
5. Integration with Game/Offseason tabs

**Deliverable**: Production-ready calendar with all advanced features

---

## Integration Points

### With Other Tabs

| Source Tab | Integration | Action |
|------------|-------------|--------|
| **Season Tab** | Timeline widget | Show games for current week |
| **League Tab** | Standings updates | Link to games that affected standings |
| **Offseason Tab** | Deadline reminders | Highlight upcoming deadlines |
| **Game Tab** | Box scores | Click game → view full game details |

### With Backend Systems

| System | Purpose | API |
|--------|---------|-----|
| **EventDatabaseAPI** | Retrieve all events | `get_events_in_date_range()` |
| **GameEvent** | Game information | Parse event data |
| **DeadlineEvent** | Offseason deadlines | Parse event data |
| **SeasonPhaseTracker** | Current phase | Determine "today" context |

---

## Future Enhancements

### Post-Launch Features

1. **Event Notifications**: Alert user X days before important deadlines
2. **Calendar Sync**: Export to external calendars (iCal, Google Calendar)
3. **Custom Events**: User-created reminders and notes
4. **Multi-Dynasty View**: Toggle between dynasties
5. **Historical Replay**: "Time travel" to past dates and replay decisions
6. **Mobile Responsive**: Adapt calendar for different screen sizes

---

## Appendix

### Example Event Data Structures

**GAME Event:**
```json
{
  "event_id": "game_20241110_phi_dal",
  "event_type": "GAME",
  "timestamp": "2024-11-10T20:15:00",
  "game_id": "game_20241110_phi_dal",
  "data": {
    "parameters": {
      "away_team_id": 23,
      "home_team_id": 6,
      "week": 10,
      "season": 2024
    },
    "results": {
      "away_score": 24,
      "home_score": 17,
      "winner_id": 23
    }
  }
}
```

**DEADLINE Event:**
```json
{
  "event_id": "deadline_franchise_tag_2025",
  "event_type": "DEADLINE",
  "timestamp": "2025-03-04T16:00:00",
  "game_id": "deadline_franchise_tag",
  "data": {
    "parameters": {
      "deadline_type": "FRANCHISE_TAG",
      "description": "Franchise Tag Deadline - 4PM ET",
      "season_year": 2025
    },
    "results": {
      "compliant_teams": 32,
      "total_teams": 32
    }
  }
}
```

---

## References

- [Event System Architecture](../architecture/offseason_event_system.md)
- [Offseason Plan](../plans/offseason_plan.md)
- [UI Development Plan](../plans/ui_development_plan.md)
- [BaseEvent Interface](../../src/events/base_event.py)
- [EventDatabaseAPI](../../src/events/event_database_api.py)

---

**End of Specification**
