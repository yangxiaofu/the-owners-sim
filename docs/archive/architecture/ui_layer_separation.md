# UI Layer Separation Architecture

**Version:** 1.0.0
**Last Updated:** 2025-10-05
**Status:** Implemented ✅

## Overview

This document describes the proper Model-View-Controller (MVC) architecture implemented in The Owner's Sim desktop UI, with emphasis on the **Domain Model Layer** that sits between controllers and database APIs.

### Key Principle

**Controllers should NOT directly access database APIs.**
Controllers should be **thin orchestration layers** that delegate business logic and data access to **domain models**.

---

## Architecture Layers

### Complete Layer Structure

```
┌─────────────────────────────────────────────────────────────┐
│                    VIEW LAYER (ui/views/)                    │
│  - Qt widgets, layouts, event handling                       │
│  - Owns UI state (current selections, filters, navigation)   │
│  - Calls controller methods for data                         │
│  - NO database access, NO business logic                     │
└─────────────────────────────────────────────────────────────┘
                             ↓ calls methods
┌─────────────────────────────────────────────────────────────┐
│                CONTROLLER LAYER (ui/controllers/)            │
│  - Thin orchestration (≤10-20 lines per method)             │
│  - Owns domain model instance(s)                             │
│  - Transforms model data for view (if needed)                │
│  - Manages Qt signals (for Qt controllers only)              │
│  - NO database access, NO complex business logic             │
└─────────────────────────────────────────────────────────────┘
                             ↓ delegates to
┌─────────────────────────────────────────────────────────────┐
│            DOMAIN MODEL LAYER (ui/domain_models/)            │  ← **NEW**
│  - Owns database API instances                               │
│  - Implements ALL business logic                             │
│  - Encapsulates data access                                  │
│  - Returns clean DTOs/dicts (no Qt dependencies)             │
│  - Reusable across different UIs                             │
└─────────────────────────────────────────────────────────────┘
                             ↓ uses
┌─────────────────────────────────────────────────────────────┐
│              DATABASE APIs (src/database/, src/events/)      │
│  - EventDatabaseAPI, DatabaseAPI, DynastyStateAPI           │
│  - TeamDataLoader, etc.                                      │
│  - Direct database operations                                │
└─────────────────────────────────────────────────────────────┘
                             ↕
┌─────────────────────────────────────────────────────────────┐
│                   Qt VIEW MODELS (ui/models/)                 │
│  - QAbstractTableModel, QAbstractListModel                   │
│  - Display formatting ONLY (colors, alignment, text)         │
│  - Owned by View, populated by Controller                    │
│  - NO database access, NO business logic                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Layer Responsibilities

### 1. View Layer (`ui/views/`)

**Examples:** `CalendarView`, `SeasonView`, `TeamView`

**✅ DOES:**
- Render UI widgets (tables, buttons, labels)
- Handle user interactions (clicks, input)
- Own UI state (current selections, filters, navigation state)
- Call controller methods to fetch data
- Update Qt view models with data from controller

**❌ DOES NOT:**
- Access database APIs directly
- Implement business logic
- Know about database structure

**Example:**
```python
class CalendarView(QWidget):
    def __init__(self, controller: CalendarController):
        self.controller = controller
        self.calendar_model = CalendarModel()  # Qt view model
        self.current_date = datetime.now()  # UI state

    def load_events(self):
        """Load events from controller."""
        year = self.current_date.year
        month = self.current_date.month

        # Call controller (thin pass-through)
        events = self.controller.get_events_for_month(year, month, self.active_filters)

        # Update Qt view model for table display
        self.calendar_model.set_events(events)
```

---

### 2. Controller Layer (`ui/controllers/`)

**Examples:** `CalendarController`, `SeasonController`, `SimulationController`

**✅ DOES:**
- Own domain model instance(s)
- Thin orchestration (≤10-20 lines per method)
- Simple data transformations for view (if needed)
- Manage Qt signals (for Qt controllers only)

**❌ DOES NOT:**
- Own database API instances
- Implement complex business logic
- Manage UI state (view's responsibility)

**Example (CORRECT):**
```python
class CalendarController:
    def __init__(self, db_path: str, dynasty_id: str, season: int):
        # Own the domain model, NOT database APIs
        self.data_model = CalendarDataModel(db_path, dynasty_id, season)

    def get_events_for_month(self, year: int, month: int, event_types=None):
        """Simple pass-through to domain model."""
        return self.data_model.get_events_for_month(year, month, event_types)

    def get_current_simulation_date(self):
        """Simple pass-through to domain model."""
        return self.data_model.get_current_simulation_date()
```

**Example (INCORRECT - DO NOT DO THIS):**
```python
class CalendarController:
    def __init__(self, db_path: str, dynasty_id: str, season: int):
        # ❌ WRONG: Controller should NOT own database APIs
        self.event_api = EventDatabaseAPI(db_path)
        self.database_api = DatabaseAPI(db_path)
        self.dynasty_api = DynastyStateAPI(db_path)

    def get_events_for_month(self, year, month):
        # ❌ WRONG: Complex business logic in controller
        # Calculate date range
        first_day = datetime(year, month, 1)
        # ... 100+ lines of complex logic ...
        # Query database directly
        events = self.event_api.get_events_by_dynasty_and_timestamp(...)
        # Merge data from multiple sources
        # Sort and filter
        return events
```

---

### 3. Domain Model Layer (`ui/domain_models/`)

**Examples:** `CalendarDataModel`, `SeasonDataModel`, `SimulationDataModel`

**✅ DOES:**
- Own ALL database API instances
- Implement ALL business logic (filtering, sorting, merging)
- Encapsulate data access
- Provide clean, reusable API to controllers
- Return simple data structures (dicts, lists, primitives)

**❌ DOES NOT:**
- Import or use Qt dependencies (`QObject`, `Signal`, etc.)
- Handle UI concerns (colors, formatting, layout)
- Directly interact with views

**Example:**
```python
class CalendarDataModel:
    """Domain model for calendar data access and business logic."""

    def __init__(self, db_path: str, dynasty_id: str, season: int):
        self.dynasty_id = dynasty_id
        self.season = season

        # OWN the database APIs
        self.event_api = EventDatabaseAPI(db_path)
        self.database_api = DatabaseAPI(db_path)
        self.dynasty_api = DynastyStateAPI(db_path)

    def get_events_for_month(self, year: int, month: int, event_types=None) -> List[Dict]:
        """
        Get events for a specific month (both scheduled and completed).

        BUSINESS LOGIC:
        1. Calculate date range (first/last day of month)
        2. Query events table for scheduled events
        3. Query games table for completed games
        4. Merge and deduplicate results
        5. Sort by timestamp
        6. Return clean data structure
        """
        # All the complex logic lives here
        first_day = datetime(year, month, 1)
        # ... date calculations ...

        # Query multiple data sources
        events = self.event_api.get_events_by_dynasty_and_timestamp(...)
        completed_games = self.database_api.get_games_by_date_range(...)

        # Merge and deduplicate
        all_items = []
        all_items.extend(events)
        # ... deduplication logic ...

        # Sort and return
        all_items.sort(key=lambda x: x['timestamp'])
        return all_items

    def get_current_simulation_date(self) -> Optional[str]:
        """Get current simulation date from dynasty_state table."""
        return self.dynasty_api.get_current_date(self.dynasty_id, self.season)
```

---

### 4. Qt View Model Layer (`ui/models/`)

**Examples:** `CalendarModel (QAbstractTableModel)`, `StatsModel`

**Purpose:** Adapter between domain data and Qt's Model/View framework.

**✅ DOES:**
- Implement Qt model interfaces (QAbstractTableModel, QAbstractListModel)
- Format data for display (date formatting, text alignment, colors)
- Provide data to Qt view widgets

**❌ DOES NOT:**
- Access database APIs
- Implement business logic
- Fetch data (receives data from controller)

**Example:**
```python
class CalendarModel(QAbstractTableModel):
    """Qt table model for calendar event display."""

    def __init__(self):
        super().__init__()
        self._events = []
        self._team_loader = TeamDataLoader()  # OK for display formatting

    def set_events(self, events: List[Dict]):
        """Receive data from controller."""
        self._events = events
        self.endResetModel()

    def data(self, index, role):
        """Format data for Qt table display."""
        if role == Qt.BackgroundRole:
            # Display formatting (colors)
            event_type = self._events[row]['event_type']
            if event_type == 'GAME':
                return QColor("#C8E6FF")  # Light blue

        if role == Qt.DisplayRole:
            # Text formatting
            return self._format_event_description(self._events[row])
```

---

## Pattern Examples

### Calendar System

```
CalendarView (UI state: current_date, active_filters)
    ↓ calls
CalendarController (thin orchestration)
    ↓ delegates to
CalendarDataModel (owns: EventDatabaseAPI, DatabaseAPI, DynastyStateAPI)
    ↓ queries
Database APIs
```

**Files:**
- `ui/views/calendar_view.py` - View layer
- `ui/controllers/calendar_controller.py` - Controller layer (4 methods, all 1-line pass-throughs)
- `ui/domain_models/calendar_data_model.py` - Domain model layer (owns 3 APIs)
- `ui/models/calendar_model.py` - Qt view model (QAbstractTableModel)

### Season/Team System

```
SeasonView (UI state: selected_team, selected_division)
    ↓ calls
SeasonController (thin orchestration)
    ↓ delegates to
SeasonDataModel (owns: TeamDataLoader, DatabaseAPI, EventDatabaseAPI, etc.)
    ↓ queries
Database APIs
```

**Files:**
- `ui/views/season_view.py` - View layer
- `ui/controllers/season_controller.py` - Controller layer (9 methods, all 1-line pass-throughs)
- `ui/domain_models/season_data_model.py` - Domain model layer (owns 5 APIs)

### Simulation System

```
SimulationController (Qt controller with signals)
    ├── owns SimulationDataModel (state persistence)
    │       ↓ uses DynastyStateAPI
    └── owns SeasonCycleController (simulation engine)
            ↓ runs actual simulation
```

**Special Case:** `SimulationController` is a Qt controller (`QObject`) that:
- Emits Qt signals for UI updates
- Owns `SeasonCycleController` (simulation engine - belongs in controller)
- Delegates state persistence to `SimulationDataModel`

---

## Benefits of This Architecture

### 1. **Testability**
- Domain models can be tested independently without Qt or UI
- No need to initialize views/widgets for business logic tests
- Fast unit tests for data access layer

### 2. **Reusability**
- Domain models can be shared across different UIs (desktop, web, CLI)
- Business logic written once, used everywhere
- Easy to add new views without duplicating logic

### 3. **Maintainability**
- Clear separation of concerns
- Changes isolated to appropriate layers
- Database schema changes only affect domain models
- UI changes only affect views

### 4. **Clarity**
- Each layer has single, well-defined responsibility
- Thin controllers are easy to understand (≤10 lines per method)
- Business logic centralized in domain models

### 5. **Scalability**
- Easy to add new domain models for new features
- Controllers stay thin regardless of complexity
- No controller bloat

---

## Migration Summary

### Before Refactoring (Violated MVC)

**CalendarController:**
- 323 lines total
- Owned 3 database APIs
- 116 lines of complex business logic in single method
- Mixed data access, business logic, and UI orchestration

**SeasonController:**
- 256 lines total
- Owned 5 database APIs
- Complex schedule generation logic (56 lines)
- Mixed responsibilities

### After Refactoring (Proper MVC)

**CalendarController:**
- 89 lines total (**-72% reduction**)
- 0 database APIs (delegated to domain model)
- 4 methods, all 1-line pass-throughs
- Pure thin orchestration

**SeasonController:**
- 151 lines total (**-41% reduction**)
- 0 database APIs (delegated to domain model)
- 9 methods, all 1-line pass-throughs
- Pure thin orchestration

**Domain Models Created:**
- `CalendarDataModel` (319 lines) - owns 3 APIs
- `SeasonDataModel` (381 lines) - owns 5 APIs
- `SimulationDataModel` (280 lines) - owns 1 API

---

## Guidelines for New Features

### When Adding a New Controller

1. **Create domain model first:**
   ```python
   # ui/domain_models/my_feature_data_model.py
   class MyFeatureDataModel:
       def __init__(self, db_path, dynasty_id, season):
           # Own database APIs here
           self.my_api = MyDatabaseAPI(db_path)

       def get_data(self):
           # Business logic here
           pass
   ```

2. **Create thin controller:**
   ```python
   # ui/controllers/my_feature_controller.py
   class MyFeatureController:
       def __init__(self, db_path, dynasty_id, season):
           self.data_model = MyFeatureDataModel(db_path, dynasty_id, season)

       def get_data(self):
           return self.data_model.get_data()  # Simple pass-through
   ```

3. **Create view:**
   ```python
   # ui/views/my_feature_view.py
   class MyFeatureView(QWidget):
       def __init__(self, controller):
           self.controller = controller
           self.load_data()

       def load_data(self):
           data = self.controller.get_data()
           # Update UI with data
   ```

### Code Review Checklist

**Controllers:**
- ✅ Owns domain model instance(s)
- ✅ Methods are ≤10-20 lines (mostly ≤10)
- ✅ No database API imports
- ✅ No complex business logic
- ❌ Does NOT own database APIs
- ❌ Does NOT have 50+ line methods

**Domain Models:**
- ✅ Owns all database API instances
- ✅ All business logic encapsulated
- ✅ Returns clean data structures (dicts, lists)
- ✅ No Qt dependencies
- ❌ Does NOT import Qt classes
- ❌ Does NOT have UI concerns

**Views:**
- ✅ Owns UI state
- ✅ Calls controller for data
- ✅ Updates Qt view models
- ❌ Does NOT access database APIs
- ❌ Does NOT implement business logic

---

## References

- **Domain Models:** `ui/domain_models/` package and `__init__.py` docstring
- **Controller Examples:** `ui/controllers/calendar_controller.py` (reference implementation)
- **UI Development Plan:** `docs/plans/ui_development_plan.md`
- **MVC Pattern:** https://en.wikipedia.org/wiki/Model%E2%80%93view%E2%80%93controller

---

**Last Updated:** 2025-10-05
**Author:** Claude Code
**Status:** Production ✅
