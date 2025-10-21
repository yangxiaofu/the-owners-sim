# Event Scheduler Module

Comprehensive NFL offseason event scheduling system for the UI demo.

## Overview

The `event_scheduler.py` module schedules all major NFL offseason events using the existing event system (`DeadlineEvent`, `WindowEvent`, `MilestoneEvent`). It provides a complete offseason timeline from February through September with proper dynasty isolation.

## Features

- **14 Offseason Events**: Complete NFL offseason timeline (Feb 9 - Sep 5)
- **Dynasty Isolation**: All events tagged with dynasty_id for multi-save support
- **Event Type Variety**: Deadlines (6), Windows (4), and Milestones (5)
- **Database Integration**: Direct EventDatabaseAPI integration
- **Command-Line Interface**: Full CLI for testing and management
- **Programmatic API**: Clean Python API for UI integration

## Event Schedule

### February 2025
- **Feb 9**: Super Bowl LIX (Milestone)

### March 2025
- **Mar 1**: NFL Combine Results Released (Milestone)
- **Mar 5**: Franchise Tag Deadline (Deadline)
- **Mar 11**: Legal Tampering Period Starts (Window START)
- **Mar 13**: Legal Tampering Period Ends (Window END)
- **Mar 13**: Free Agency Opens (Deadline)
- **Mar 13**: Free Agency Period Starts (Window START)

### April 2025
- **Apr 24**: NFL Draft Starts (Deadline)
- **Apr 27**: NFL Draft Ends (Deadline)

### May 2025
- **May 20**: OTAs Begin (Milestone)

### July 2025
- **Jul 23**: Training Camp Opens (Milestone)

### August 2025
- **Aug 26**: Roster Cuts to 53 (Deadline)

### September 2025
- **Sep 5**: Regular Season Begins (Milestone)
- **Sep 5**: Free Agency Period Ends (Window END)

## Usage

### Programmatic API (Recommended for UI)

```python
from demo.offseason_demo.event_scheduler import schedule_offseason_events, get_event_calendar_summary

# Schedule all offseason events
event_ids = schedule_offseason_events(
    database_path="data/database/nfl_simulation.db",
    dynasty_id="ui_offseason_demo",
    season_year=2024
)

print(f"Scheduled {len(event_ids)} events")

# Get summary of scheduled events
summary = get_event_calendar_summary(
    database_path="data/database/nfl_simulation.db",
    dynasty_id="ui_offseason_demo",
    season_year=2024
)

print(f"Total: {summary['total_events']} events")
print(f"Deadlines: {summary['deadline_count']}")
print(f"Windows: {summary['window_count']}")
print(f"Milestones: {summary['milestone_count']}")
print(f"Date Range: {summary['earliest_date']} to {summary['latest_date']}")
```

### Command-Line Interface

```bash
# Schedule events
PYTHONPATH=src python demo/offseason_demo/event_scheduler.py \
    --database="data/database/nfl_simulation.db" \
    --dynasty="ui_offseason_demo" \
    --season=2024

# Clear existing events before scheduling
PYTHONPATH=src python demo/offseason_demo/event_scheduler.py \
    --database="data/database/nfl_simulation.db" \
    --dynasty="ui_offseason_demo" \
    --season=2024 \
    --clear

# Show summary only (don't schedule)
PYTHONPATH=src python demo/offseason_demo/event_scheduler.py \
    --database="data/database/nfl_simulation.db" \
    --dynasty="ui_offseason_demo" \
    --season=2024 \
    --summary
```

### Clear Events

```python
from demo.offseason_demo.event_scheduler import clear_offseason_events

# WARNING: This deletes ALL events for the dynasty
deleted_count = clear_offseason_events(
    database_path="data/database/nfl_simulation.db",
    dynasty_id="ui_offseason_demo"
)

print(f"Deleted {deleted_count} events")
```

## API Reference

### `schedule_offseason_events()`

Schedule all NFL offseason events.

**Parameters:**
- `database_path` (str): Path to SQLite database file
- `dynasty_id` (str, optional): Dynasty context for isolation (default: "ui_offseason_demo")
- `season_year` (int, optional): Season year - offseason is year+1 (default: 2024)

**Returns:**
- `List[str]`: List of event IDs created

**Raises:**
- `Exception`: If database operations fail

**Example:**
```python
event_ids = schedule_offseason_events(
    database_path="data/database/nfl_simulation.db",
    dynasty_id="my_dynasty",
    season_year=2024
)
# Returns: ['event-id-1', 'event-id-2', ..., 'event-id-14']
```

### `get_event_calendar_summary()`

Get summary of scheduled offseason events.

**Parameters:**
- `database_path` (str): Path to SQLite database file
- `dynasty_id` (str, optional): Dynasty context (default: "ui_offseason_demo")
- `season_year` (int, optional): Season year (default: 2024)

**Returns:**
- `Dict[str, Any]`: Dictionary with event counts and details
  - `total_events` (int): Total number of events
  - `deadline_count` (int): Number of deadline events
  - `window_count` (int): Number of window events
  - `milestone_count` (int): Number of milestone events
  - `earliest_date` (datetime): Earliest event date
  - `latest_date` (datetime): Latest event date
  - `dynasty_id` (str): Dynasty identifier
  - `season_year` (int): Season year
  - `database_path` (str): Database path

**Example:**
```python
summary = get_event_calendar_summary("data/database/nfl_simulation.db")
print(f"Total events: {summary['total_events']}")
print(f"Deadlines: {summary['deadline_count']}")
print(f"Windows: {summary['window_count']}")
print(f"Milestones: {summary['milestone_count']}")
```

### `clear_offseason_events()`

Clear all offseason events for a specific dynasty.

**WARNING:** This will delete ALL events for the specified dynasty. Use with caution.

**Parameters:**
- `database_path` (str): Path to SQLite database file
- `dynasty_id` (str, optional): Dynasty context to clear (default: "ui_offseason_demo")

**Returns:**
- `int`: Number of events deleted

**Raises:**
- `Exception`: If database operations fail

**Example:**
```python
deleted = clear_offseason_events("data/database/nfl_simulation.db", "test_dynasty")
print(f"Deleted {deleted} events")
```

## Event Breakdown

| Event Type | Count | Examples |
|------------|-------|----------|
| Deadline | 6 | Franchise Tag Deadline, Draft Start, Roster Cuts |
| Window | 4 | Legal Tampering START/END, Free Agency START/END |
| Milestone | 5 | Super Bowl, Combine, OTAs, Training Camp, Season Start |
| **Total** | **14** | Complete offseason timeline |

## Database Schema

All events are stored in the `events` table with the following fields:

- `event_id` (TEXT): Unique identifier (UUID)
- `event_type` (TEXT): "DEADLINE", "WINDOW", or "MILESTONE"
- `timestamp` (INTEGER): Unix timestamp in milliseconds
- `game_id` (TEXT): Event identifier (e.g., "deadline_2024_FRANCHISE_TAG")
- `dynasty_id` (TEXT): Dynasty context for isolation
- `data` (TEXT): JSON event data including parameters and metadata

## Dynasty Isolation

Each event is tagged with a `dynasty_id` to support multiple concurrent save files. This allows the UI to:

1. Schedule events for different dynasties independently
2. Query events by dynasty without cross-contamination
3. Delete events for one dynasty without affecting others
4. Support multiple users with separate calendars

## Integration with UI

### Initialization
```python
# When user starts offseason phase
from demo.offseason_demo.event_scheduler import schedule_offseason_events

event_ids = schedule_offseason_events(
    database_path=ui_database_path,
    dynasty_id=current_dynasty_id,
    season_year=current_season
)
```

### Calendar Display
```python
# Query events via EventDatabaseAPI
from events.event_database_api import EventDatabaseAPI

event_db = EventDatabaseAPI(ui_database_path)

# Get all events for current dynasty
all_events = event_db.get_events_by_dynasty(dynasty_id=current_dynasty_id)

# Filter by date range for calendar month view
from datetime import datetime
start_ms = int(datetime(2025, 3, 1).timestamp() * 1000)
end_ms = int(datetime(2025, 4, 1).timestamp() * 1000)

march_events = event_db.get_events_by_dynasty_and_timestamp(
    dynasty_id=current_dynasty_id,
    start_timestamp_ms=start_ms,
    end_timestamp_ms=end_ms
)
```

### Cleanup
```python
# When resetting dynasty or starting new season
from demo.offseason_demo.event_scheduler import clear_offseason_events

deleted = clear_offseason_events(ui_database_path, current_dynasty_id)
```

## Testing

Run the test suite:

```bash
# Test with real database
PYTHONPATH=src python demo/offseason_demo/event_scheduler.py \
    --database="data/database/nfl_simulation.db" \
    --dynasty="test_dynasty" \
    --season=2024 \
    --clear

# Verify events were created
PYTHONPATH=src python demo/offseason_demo/event_scheduler.py \
    --database="data/database/nfl_simulation.db" \
    --dynasty="test_dynasty" \
    --season=2024 \
    --summary
```

## Error Handling

The module includes comprehensive error handling:

- **Database Errors**: All database operations wrapped in try/except
- **Validation**: Event data validated before insertion
- **Logging**: Full event-level logging for debugging
- **Transaction Safety**: Events created in sequence with rollback on failure
- **Clear Feedback**: Success/failure counts reported for all operations

## Performance

- **Batch Operations**: Uses EventDatabaseAPI for efficient database operations
- **Indexed Queries**: Dynasty and timestamp indexes for fast retrieval
- **Minimal Overhead**: Direct API calls without intermediate layers
- **Scalability**: Supports thousands of events across multiple dynasties

## Dependencies

```python
from events.deadline_event import DeadlineEvent, DeadlineType
from events.window_event import WindowEvent, WindowName
from events.milestone_event import MilestoneEvent, MilestoneType
from events.event_database_api import EventDatabaseAPI
from calendar.date_models import Date
```

## Future Enhancements

Potential improvements for future versions:

1. **Configurable Events**: JSON configuration file for event dates
2. **Event Templates**: Reusable event templates for different seasons
3. **Validation Rules**: Business logic validation (e.g., no overlapping deadlines)
4. **Batch Insert**: Use `insert_events()` for better performance
5. **Event Metadata**: Additional metadata for UI display (icons, colors, priorities)
6. **Recurring Events**: Support for annual recurring events

## Changelog

### Version 1.0.0 (Oct 2025)
- Initial implementation
- 14 offseason events (Feb-Sep)
- Dynasty isolation support
- Command-line interface
- Programmatic API
- Event summary and cleanup utilities

## License

Part of The Owners Sim project.

## Contact

See main project CLAUDE.md for development guidelines and architecture documentation.
