# Offseason Demo Domain Models

This document describes the domain models created for the offseason UI demo.

## Overview

Three domain models provide clean interfaces for UI components to interact with offseason simulation data:

1. **OffseasonDemoDataModel** - Offseason state and deadline management
2. **CalendarDemoDataModel** - Calendar events and scheduling
3. **TeamDemoDataModel** - Team information, roster, and cap space

All models use `dynasty_id="ui_offseason_demo"` and query from the demo database at `demo/offseason_demo/offseason_demo.db`.

## Architecture Pattern

These models follow the **Domain Model Pattern** described in `ui/domain_models/calendar_data_model.py`:

```
View → Controller → Domain Model → Database API → SQLite
```

**Key Principles:**
- **No Qt dependencies** - Models can be tested without UI
- **No UI concerns** - No colors, formatting, or widget logic
- **Clean data structures** - Returns dicts and lists
- **Owns database APIs** - Each model owns its API instances
- **Business logic layer** - Encapsulates all query patterns

## 1. OffseasonDemoDataModel

Manages offseason state, phases, and calendar advancement.

### Initialization

```python
from demo.offseason_demo.demo_domain_models import OffseasonDemoDataModel

model = OffseasonDemoDataModel(
    database_path="demo/offseason_demo/offseason_demo.db",
    dynasty_id="ui_offseason_demo",
    season_year=2025,
    user_team_id=22  # Detroit Lions
)
```

### Key Methods

#### `get_current_phase() -> str`
Returns current offseason phase (e.g., `"post_super_bowl"`).

#### `get_current_phase_display_name() -> str`
Returns human-readable phase name (e.g., `"Post Super Bowl"`).

#### `get_current_date() -> datetime`
Returns current simulation date.

#### `get_upcoming_deadlines(limit: int = 5) -> List[Dict[str, Any]]`
Returns upcoming deadlines with days remaining.

```python
deadlines = model.get_upcoming_deadlines(5)
# [
#     {
#         'type': 'FRANCHISE_TAG_DEADLINE',
#         'date': date(2026, 3, 5),
#         'description': 'Franchise tag deadline',
#         'days_remaining': 24
#     },
#     ...
# ]
```

#### `get_state_summary() -> Dict[str, Any]`
Returns comprehensive state summary:

```python
summary = model.get_state_summary()
# {
#     'dynasty_id': 'ui_offseason_demo',
#     'season_year': 2025,
#     'current_date': datetime(2026, 2, 9),
#     'current_phase': 'post_super_bowl',
#     'current_phase_display': 'Post Super Bowl',
#     'offseason_complete': False,
#     'upcoming_deadlines': [...],
#     'actions_taken': 0
# }
```

#### `advance_day() -> Dict[str, Any]`
Advances calendar by 1 day and triggers events.

```python
result = model.advance_day()
# {
#     'new_date': datetime(2026, 2, 10),
#     'phase_changed': False,
#     'new_phase': None,
#     'deadlines_passed': [],
#     'events_triggered': []
# }
```

#### `advance_to_deadline(deadline_type: str) -> Dict[str, Any]`
Jumps calendar to next occurrence of deadline.

```python
result = model.advance_to_deadline('FRANCHISE_TAG_DEADLINE')
# {
#     'deadline_type': 'FRANCHISE_TAG_DEADLINE',
#     'deadline_date': date(2026, 3, 5),
#     'days_advanced': 24,
#     'current_phase': 'franchise_tag_period',
#     'events_triggered': [...]
# }
```

#### `is_offseason_complete() -> bool`
Checks if offseason is complete (ready for next season).

### Internal Components

Uses `OffseasonController` from `src/offseason/offseason_controller.py` for all operations.

---

## 2. CalendarDemoDataModel

Manages calendar events and game scheduling.

### Initialization

```python
from demo.offseason_demo.demo_domain_models import CalendarDemoDataModel

model = CalendarDemoDataModel(
    database_path="demo/offseason_demo/offseason_demo.db",
    dynasty_id="ui_offseason_demo",
    season=2025
)
```

### Key Methods

#### `get_events_for_month(year: int, month: int, event_types: Optional[List[str]] = None) -> List[Dict[str, Any]]`
Returns all events for a specific month.

```python
# Get all events for March 2025
events = model.get_events_for_month(2025, 3)

# Get only GAME events for March 2025
games = model.get_events_for_month(2025, 3, event_types=['GAME'])

# Get only deadline events
deadlines = model.get_events_for_month(2025, 3, event_types=['DEADLINE', 'WINDOW'])
```

**Event Structure:**
```python
{
    'event_id': str,
    'event_type': str,  # 'GAME', 'DEADLINE', 'WINDOW', 'MILESTONE', etc.
    'timestamp': int or datetime,
    'game_id': str,
    'dynasty_id': str,
    'data': {
        'parameters': {...},
        'results': {...},
        'metadata': {...}
    }
}
```

#### `get_events_for_date_range(start_date: datetime, end_date: datetime, event_types: Optional[List[str]] = None) -> List[Dict[str, Any]]`
Returns events within a date range.

```python
from datetime import datetime

start = datetime(2025, 3, 1)
end = datetime(2025, 3, 31)
events = model.get_events_for_date_range(start, end)
```

#### `get_event_details(event_id: str) -> Optional[Dict[str, Any]]`
Returns full details for a specific event.

```python
details = model.get_event_details('event_123')
# Returns event dict or None if not found
```

#### `get_all_offseason_events() -> List[Dict[str, Any]]`
Returns all scheduled offseason events (not GAME events).

```python
offseason_events = model.get_all_offseason_events()
# Returns DEADLINE, WINDOW, MILESTONE, FRANCHISE_TAG, etc.
```

### Data Sources

Queries both:
1. **events table** - Scheduled events (including future games)
2. **games table** - Completed games with results

Automatically deduplicates to avoid showing same game twice.

### Internal Components

Uses:
- `EventDatabaseAPI` - Query events table
- `DatabaseAPI` - Query games table
- `DynastyStateAPI` - Query dynasty state

---

## 3. TeamDemoDataModel

Manages team data including roster and cap space.

### Initialization

```python
from demo.offseason_demo.demo_domain_models import TeamDemoDataModel

model = TeamDemoDataModel(
    database_path="demo/offseason_demo/offseason_demo.db",
    dynasty_id="ui_offseason_demo",
    season=2025
)
```

### Key Methods

#### `get_team_info(team_id: int) -> Dict[str, Any]`
Returns team metadata.

```python
info = model.get_team_info(22)  # Detroit Lions
# {
#     'team_id': 22,
#     'name': 'Detroit Lions',
#     'abbreviation': 'DET',
#     'city': 'Detroit',
#     'division': 'NFC North',
#     'conference': 'NFC',
#     'primary_color': '#0076B6',
#     'secondary_color': '#B0B7BC'
# }
```

#### `get_team_roster(team_id: int) -> List[Dict[str, Any]]`
Returns team roster (mock data for demo).

```python
roster = model.get_team_roster(22)
# [
#     {
#         'player_id': 'player_22_1',
#         'name': 'Starting QB',
#         'position': 'QB',
#         'jersey_number': 9,
#         'depth_position': 1,
#         'years_in_league': 5,
#         'contract_years_remaining': 2,
#         'contract_avg_value': 45_000_000
#     },
#     ...
# ]
```

#### `get_team_cap_space(team_id: int) -> Dict[str, Any]`
Returns salary cap information (mock data).

```python
cap_space = model.get_team_cap_space(22)
# {
#     'cap_limit': 200_000_000,
#     'cap_used': 174_709_988,
#     'cap_space': 25_290_012,
#     'top_51_total': 174_709_988,
#     'contracts_count': 49,
#     'projected_cap_space': 35_290_012
# }
```

#### `get_team_upcoming_free_agents(team_id: int) -> List[Dict[str, Any]]`
Returns players with expiring contracts (mock data).

```python
ufas = model.get_team_upcoming_free_agents(22)
# [
#     {
#         'player_id': 'ufa_22_1',
#         'name': 'Star RB',
#         'position': 'RB',
#         'age': 26,
#         'years_with_team': 3,
#         'last_contract_aav': 8_000_000,
#         'estimated_market_value': 12_000_000,
#         'priority': 'HIGH',
#         'recommendation': 'Re-sign or franchise tag'
#     },
#     ...
# ]
```

### Mock Data Notes

- Team roster, cap space, and UFAs use **mock data** for demo
- In production, these would query actual database tables
- Team info for Detroit Lions (22) is hard-coded; other teams use defaults

### Internal Components

Uses:
- `DatabaseAPI` - Query team data
- `CapDatabaseAPI` - Query salary cap data (placeholder for now)

---

## Testing

Run verification tests:

```bash
cd demo/offseason_demo
PYTHONPATH=../../src python3 test_domain_models.py
```

**Expected Output:**
```
✓ OffseasonDemoDataModel tests passed!
✓ CalendarDemoDataModel tests passed!
✓ TeamDemoDataModel tests passed!
✓ ALL DOMAIN MODEL TESTS PASSED!
```

---

## Usage in UI Controllers

Example integration in a controller:

```python
class OffseasonController:
    def __init__(self, main_window):
        self.main_window = main_window

        # Initialize domain model
        self.data_model = OffseasonDemoDataModel(
            database_path="demo/offseason_demo/offseason_demo.db",
            dynasty_id="ui_offseason_demo",
            season_year=2025,
            user_team_id=22
        )

    def on_advance_day_clicked(self):
        """Handle advance day button click."""
        # Delegate to domain model
        result = self.data_model.advance_day()

        # Update view with results
        self.view.update_current_date(result['new_date'])

        if result['phase_changed']:
            self.view.update_phase_display(result['new_phase'])

        if result['deadlines_passed']:
            self.view.show_deadline_notifications(result['deadlines_passed'])
```

**Key Pattern:**
1. Controller delegates ALL data access to domain model
2. Domain model returns clean data structures
3. Controller updates view with results
4. No database queries in controller

---

## Files

- **demo_domain_models.py** - All 3 domain model classes
- **test_domain_models.py** - Verification tests
- **DOMAIN_MODELS.md** - This documentation

---

## References

- Domain Model Pattern: `ui/domain_models/calendar_data_model.py`
- UI Architecture: `docs/architecture/ui_layer_separation.md`
- Offseason System: `src/offseason/offseason_controller.py`
- Database APIs: `src/events/event_database_api.py`, `src/database/api.py`
