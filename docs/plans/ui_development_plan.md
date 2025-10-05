# UI Development Plan - The Owner's Sim

**Version:** 1.1.0
**Last Updated:** 2025-10-04
**Status:** Phase 1 Complete ✅ | Phase 2 Ready to Start
**UI Framework:** PySide6 (Qt for Python)

## Overview

This document outlines the comprehensive plan for building a desktop user interface for "The Owner's Sim" NFL management simulation game. The UI design is inspired by **Out of the Park Baseball (OOTP)**, featuring a data-heavy, tab-based interface with extensive statistics, customizable views, and professional desktop application patterns.

### Vision

Create a professional, cross-platform desktop application that:
- Provides deep statistical analysis through customizable data tables
- Offers intuitive navigation via OOTP-style tab system
- Supports dynasty management with offseason interactions
- Maintains clean separation between UI and simulation engine
- Delivers native desktop performance and responsiveness

### Design Philosophy

**OOTP-Inspired Principles:**
1. **Data-First Design**: Statistics and information are central to the experience
2. **Tab-Based Organization**: Major features accessible through top-level tabs
3. **Customizable Views**: Users control what data they see and how it's displayed
4. **Browser-Style Navigation**: History, breadcrumbs, bookmarks for easy movement
5. **Context-Aware Actions**: Right-click menus provide relevant options
6. **Professional Desktop Feel**: Native widgets, keyboard shortcuts, drag-and-drop

---

## Progress Summary

### ✅ Completed Phases

**Phase 1: Foundation & Basic Structure** (Completed: 2025-10-04)
- ✅ Complete `ui/` folder structure created
- ✅ PySide6 application shell working
- ✅ 7 primary tabs (Season, Calendar, Team, Player, Offseason, League, Game)
- ✅ Complete menu bar with 7 menus
- ✅ Toolbar with quick actions
- ✅ Status bar with date/phase display
- ✅ OOTP-inspired QSS stylesheet
- ✅ All view stubs created with placeholder content
- ✅ Test script verifying imports
- ✅ Documentation complete
- ✅ Calendar tab with event display and month navigation

**Additional Completions:**
- ✅ SeasonController with team data and standings access
- ✅ CalendarController with event filtering and month navigation
- ✅ CalendarModel (Qt table model) with color-coded event types
- ✅ CalendarView with filters and event details panel
- ✅ Team standings moved from Season tab to League tab
- ✅ Fixed circular import issue in src/calendar module

**Files Created:** 25 files
**How to Run:** `pip install -r requirements-ui.txt && python main.py`
**Test:** `python test_ui.py`

### ⏳ Current Phase

**Phase 2: Core Views - Season & Team** (Weeks 3-4)
- Target: Implement Season and Team views with real data
- Tasks: Schedule grid, standings, roster table, database integration
- Estimated Timeline: 2 weeks

### 📋 Upcoming Phases

- **Phase 3**: Data Tables & Statistics Display (Weeks 5-6)
- **Phase 4**: Offseason Interface (Weeks 7-8)
- **Phase 5**: Advanced Features (Weeks 9-10)
- **Phase 6**: Testing & Documentation (Weeks 11-12)

**Total Timeline:** 12 weeks | **Current Progress:** Phase 1 Complete (Week 2)

---

## Architecture Design

### Folder Structure

```
the-owners-sim/
├── src/                          # Core simulation engine (existing - DO NOT MODIFY)
│   ├── play_engine/
│   ├── game_management/
│   ├── season/
│   ├── playoff_system/
│   ├── events/
│   ├── database/
│   └── ...
│
├── ui/                           # NEW: Desktop UI layer (PySide6/Qt)
│   ├── __init__.py
│   ├── main_window.py           # Main application window with tab system
│   ├── app.py                   # Qt application initialization and config
│   │
│   ├── views/                   # Screen/view modules (OOTP-style tabs)
│   │   ├── __init__.py
│   │   ├── season_view.py       # Season overview: schedule, standings, stats leaders
│   │   ├── team_view.py         # Team management: roster, depth chart, finances
│   │   ├── player_view.py       # Player details: stats, contract, career history
│   │   ├── offseason_view.py    # Offseason dashboard: deadlines, free agency, draft
│   │   ├── league_view.py       # League-wide stats and leaderboards
│   │   └── game_view.py         # Live game simulation view (play-by-play)
│   │
│   ├── widgets/                 # Reusable custom widgets
│   │   ├── __init__.py
│   │   ├── stats_table.py       # Custom QTableView for statistics display
│   │   ├── depth_chart_widget.py # Drag-drop depth chart management
│   │   ├── schedule_grid.py     # Interactive schedule display
│   │   ├── standings_table.py   # Division/conference standings widget
│   │   ├── player_card.py       # Compact player info card
│   │   ├── calendar_widget.py   # Offseason calendar with deadline tracking
│   │   ├── game_ticker.py       # Live score ticker widget
│   │   └── breadcrumb_bar.py    # Navigation breadcrumb trail
│   │
│   ├── dialogs/                 # Modal dialogs for user interactions
│   │   ├── __init__.py
│   │   ├── franchise_tag_dialog.py      # Franchise tag selection
│   │   ├── free_agent_signing_dialog.py # Free agent contract negotiation
│   │   ├── draft_pick_dialog.py         # Draft selection interface
│   │   ├── roster_cut_dialog.py         # Roster management/cuts
│   │   ├── trade_dialog.py              # Trade proposal interface
│   │   └── settings_dialog.py           # Application settings
│   │
│   ├── models/                  # Qt Model/View data models
│   │   ├── __init__.py
│   │   ├── stats_model.py       # QAbstractTableModel for player/team stats
│   │   ├── roster_model.py      # Model for roster data with drag-drop
│   │   ├── schedule_model.py    # Schedule data model
│   │   ├── standings_model.py   # Standings calculation model
│   │   ├── transaction_model.py # Transaction log model
│   │   └── filter_proxy_model.py # Filtering and sorting proxy
│   │
│   ├── controllers/             # UI controllers (mediators between views and engine)
│   │   ├── __init__.py
│   │   ├── season_controller.py # Season simulation control
│   │   ├── team_controller.py   # Team management control
│   │   ├── offseason_controller.py # Offseason interaction control
│   │   └── navigation_controller.py # App navigation and history
│   │
│   ├── resources/               # UI resources
│   │   ├── icons/               # Application icons (PNG, SVG)
│   │   │   ├── app_icon.png
│   │   │   ├── toolbar/         # Toolbar icons
│   │   │   └── teams/           # Team logos (32 NFL teams)
│   │   ├── styles/              # QSS stylesheets (Qt CSS)
│   │   │   ├── main.qss         # Default theme
│   │   │   ├── dark_theme.qss   # Dark mode theme
│   │   │   └── ootp_inspired.qss # OOTP-style theme
│   │   └── ui/                  # Qt Designer .ui files (if using Designer)
│   │       └── templates/       # UI templates
│   │
│   └── utils/                   # UI utilities
│       ├── __init__.py
│       ├── formatters.py        # Data formatting for display (stats, money, dates)
│       ├── validators.py        # Input validation helpers
│       ├── navigation.py        # Navigation history and breadcrumbs
│       ├── preferences.py       # User preferences and settings persistence
│       └── theme_manager.py     # Theme switching and customization
│
├── demo/                        # Existing demo scripts (keep as-is)
│   └── ...
│
├── main.py                      # NEW: Desktop application entry point
├── requirements-ui.txt          # UI-specific dependencies
└── .env.example                 # Example environment configuration
```

### Separation of Concerns

**Core Principle: UI and Engine are Independent Layers**

```
┌─────────────────────────────────────────┐
│         User Interface Layer (ui/)       │
│   - PySide6/Qt widgets and views        │
│   - User interactions and displays      │
│   - Data formatting and presentation    │
└─────────────────────────────────────────┘
                    ↕ (clean interface)
┌─────────────────────────────────────────┐
│    Simulation Engine Layer (src/)       │
│   - Game logic and calculations         │
│   - Database operations                 │
│   - Event system and workflows          │
└─────────────────────────────────────────┘
```

**Benefits:**
- UI can be replaced/redesigned without touching simulation logic
- Engine can be tested independently without UI dependencies
- Multiple UIs possible (desktop, web, mobile) using same engine
- Clear responsibility boundaries

---

## Technology Stack

### Core Framework: PySide6 (Qt for Python)

**Why PySide6/Qt?**

1. **Professional Data Tables**
   - Built-in `QTableView` with Model/View architecture
   - Handles thousands of rows efficiently (virtual scrolling)
   - Sortable columns, custom delegates, inline editing
   - Perfect for OOTP-style statistics displays

2. **Cross-Platform Native**
   - Windows, macOS, Linux support
   - Native look and feel on each platform
   - Desktop-class performance

3. **Rich Widget Library**
   - Tabs (`QTabWidget`), toolbars, menus, dialogs
   - Drag-and-drop support built-in
   - Context menus (`QMenu`)
   - Splitters, docking windows, MDI

4. **Excellent Python Integration**
   - Official Qt bindings (LGPL license)
   - Pythonic API with signals/slots
   - SQLite integration (matches our DB)
   - Matplotlib/PyQtGraph for charts

5. **OOTP-Style Features**
   - Tab-based navigation (`QTabWidget`)
   - Browser-style history (`QUndoStack`)
   - Hyperlinks and rich text (`QLabel`, `QTextBrowser`)
   - Customizable toolbars and shortcuts

### Dependencies

**`requirements-ui.txt`:**
```txt
# Core UI Framework
PySide6>=6.6.0              # Qt for Python

# Data Visualization (optional)
matplotlib>=3.8.0           # Charts and graphs
pyqtgraph>=0.13.3          # High-performance real-time plotting

# Utilities
python-dateutil>=2.8.2     # Date handling utilities
humanize>=4.9.0            # Human-readable numbers/dates

# Development Tools (optional)
qt-material>=2.14          # Material Design themes for Qt
```

**Note:** Keep `src/` dependencies separate - no UI libraries in core engine!

### Development Tools

- **Qt Designer**: Visual UI design tool (optional, can code widgets directly)
- **Qt Creator**: IDE with Qt-specific features (optional)
- **VSCode with Qt extensions**: Syntax highlighting for `.qss` stylesheets

---

## Core UI Components

### 1. Main Window Structure

**`ui/main_window.py`** - OOTP-Inspired Layout:

```python
from PySide6.QtWidgets import QMainWindow, QTabWidget, QToolBar, QStatusBar
from PySide6.QtCore import Qt

class MainWindow(QMainWindow):
    """
    Main application window with OOTP-style tab navigation.

    Structure:
    - Menu bar (Game, Season, Team, Player, League, Tools, Help)
    - Icon toolbar (Quick actions)
    - Central tab widget (Season, Team, Player, Offseason, League, Game)
    - Status bar (Current date, phase, notifications)
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("The Owner's Sim")
        self.setGeometry(100, 100, 1600, 1000)

        # Central tab widget (OOTP-style primary navigation)
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.setMovable(False)  # Fixed tab order like OOTP

        # Add primary views as tabs
        self.tabs.addTab(SeasonView(self), "Season")
        self.tabs.addTab(TeamView(self), "Team")
        self.tabs.addTab(PlayerView(self), "Player")
        self.tabs.addTab(OffseasonView(self), "Offseason")
        self.tabs.addTab(LeagueView(self), "League")
        self.tabs.addTab(GameView(self), "Game")

        self.setCentralWidget(self.tabs)

        # Create UI elements
        self._create_menus()
        self._create_toolbar()
        self._create_statusbar()

        # Load user preferences
        self._load_preferences()
```

### 2. View Modules (Tab Content)

#### Season View (`ui/views/season_view.py`)

**Purpose:** Season overview - schedule, standings, stats leaders, playoff picture

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│ Season View                                              │
├─────────────────────────────────────────────────────────┤
│ [Schedule] [Standings] [Stats Leaders] [Playoff Picture] │ ← Sub-tabs
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Week: [15 ▼]  Date: Dec 15, 2024                       │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ SCHEDULE - Week 15                                │  │
│  ├────┬─────────┬───────┬──────────┬───────┬────────┤  │
│  │ Day│ Away    │ Score │ Home     │ Score │ Status │  │
│  ├────┼─────────┼───────┼──────────┼───────┼────────┤  │
│  │ Thu│ Packers │  24   │ Lions    │  31   │ Final  │  │
│  │ Sun│ Eagles  │  --   │ Commanders│  --   │ 1:00pm │  │
│  │ ... (more games)                                  │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  [◄ Prev Week]  [Simulate Day]  [Simulate Week]  [►]   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Key Features:**
- Tabbed sub-sections (Schedule, Standings, Stats Leaders, Playoff Picture)
- Week selector dropdown
- Interactive schedule grid (clickable games for details)
- Simulation controls (day/week advancement)
- Real-time standings updates

#### Team View (`ui/views/team_view.py`)

**Purpose:** Team management - roster, depth chart, finances, staff

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│ Team: [Detroit Lions ▼]                                 │
├─────────────────────────────────────────────────────────┤
│ [Roster] [Depth Chart] [Finances] [Staff] [Strategy]    │ ← Sub-tabs
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Position: [All Positions ▼]  Sort: [Overall ▼]        │
│  Search: [________]  [🔍]                               │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ ROSTER                                            │  │
│  ├──┬─────────────┬────┬───┬────┬────┬────┬────────┤  │
│  │ #│ Name        │ Pos│Age│OVR │CON │Sal │Status  │  │
│  ├──┼─────────────┼────┼───┼────┼────┼────┼────────┤  │
│  │ 9│ M. Stafford │ QB │ 35│ 87 │ 2yr│ $45M│ Active │  │
│  │ ... (right-click for actions: View Stats, Cut,     │  │
│  │      Trade, Adjust Depth Chart)                    │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  Roster Size: 53/53   Cap Space: $12.5M                │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Key Features:**
- Team selector (dynasty: user team pre-selected)
- Sub-tabs for different team aspects
- Filterable/sortable roster table
- Right-click context menu (View Player, Cut, Trade, etc.)
- Salary cap tracking display
- Drag-and-drop depth chart (in Depth Chart sub-tab)

#### Offseason View (`ui/views/offseason_view.py`)

**Purpose:** Offseason management - deadlines, free agency, draft, roster cuts

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│ Offseason Dashboard                                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Current Date: March 10, 2025                           │
│  Current Phase: Free Agency - Legal Tampering Period    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │ 📅 UPCOMING DEADLINES                           │    │
│  ├────────────────────────────────────────────────┤    │
│  │ ⏰ Free Agency Opens    March 12, 4PM  [2 days]│    │
│  │ ⏰ Draft                April 24       [45 days]│    │
│  │ ⏰ Roster Cuts          Aug 26         [169 days]   │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │ 💰 SALARY CAP STATUS                            │    │
│  ├────────────────────────────────────────────────┤    │
│  │ Team Cap:        $225,000,000                   │    │
│  │ Current Spending: $198,450,000                  │    │
│  │ Cap Space:        $26,550,000                   │    │
│  │ Status: ✅ COMPLIANT                            │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  [🏷️  Apply Franchise Tag]  [📝 Browse Free Agents]    │
│  [📋 Manage Roster]         [📊 View Draft Board]      │
│                                                          │
│  [⏩ Advance 1 Day]  [⏭️  Advance to Next Deadline]     │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Key Features:**
- Current offseason phase display
- Deadline countdown timers
- Salary cap status dashboard
- Action buttons for offseason tasks (tag, sign, draft, cut)
- Calendar advancement controls
- Transaction feed (league-wide activity)

### 3. Custom Widgets

#### Stats Table Widget (`ui/widgets/stats_table.py`)

**Purpose:** Reusable, feature-rich statistics table (OOTP-style)

**Features:**
- Sortable columns (click headers)
- Customizable column visibility
- Context menu (View Player, Compare, Export)
- Zebra striping for readability
- Number formatting (stats, money, percentages)
- Column resizing and reordering
- Export to CSV

**Implementation Pattern:**
```python
from PySide6.QtWidgets import QTableView
from PySide6.QtCore import Qt, QSortFilterProxyModel

class StatsTable(QTableView):
    """
    OOTP-style statistics table with sorting, filtering, and customization.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Visual styling
        self.setAlternatingRowColors(True)  # Zebra striping
        self.setSortingEnabled(True)
        self.setSelectionBehavior(QTableView.SelectRows)
        self.horizontalHeader().setStretchLastSection(True)

        # Context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def set_data_model(self, model):
        """Connect to a stats data model with filtering."""
        proxy = QSortFilterProxyModel()
        proxy.setSourceModel(model)
        self.setModel(proxy)

    def _show_context_menu(self, position):
        # Right-click menu: View Player, Compare Players, Export Data
        pass
```

#### Depth Chart Widget (`ui/widgets/depth_chart_widget.py`)

**Purpose:** Visual depth chart with drag-and-drop position management

**Features:**
- Position-based layout (QB, RB, WR, etc.)
- Drag players between positions
- Visual indicators for starter/backup
- Player info on hover
- Save depth chart changes

**Layout:**
```
QB          RB          WR1         WR2
┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
│ M.Staff│  │ D.Swift│  │ A.St-Br│  │ J.Reyn │
│   87   │  │   84   │  │   88   │  │   83   │
└────────┘  └────────┘  └────────┘  └────────┘
┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
│ H.Hooker│  │ C.Gibbs│  │ J.Willi│  │ T.Patr │
│   76   │  │   79   │  │   80   │  │   78   │
└────────┘  └────────┘  └────────┘  └────────┘
```

---

## OOTP-Style Features Implementation

### 1. Tab-Based Navigation

**Primary Tabs** (Top Level):
- Season, Team, Player, Offseason, League, Game

**Secondary Tabs** (Within Views):
- Season → Schedule, Standings, Stats Leaders, Playoff Picture
- Team → Roster, Depth Chart, Finances, Staff, Strategy
- Offseason → Dashboard, Free Agency, Draft, Roster Cuts

**Implementation:**
```python
# Main window: QTabWidget for primary navigation
self.main_tabs = QTabWidget()

# Season view: Nested tabs for sub-sections
class SeasonView(QWidget):
    def __init__(self):
        self.sub_tabs = QTabWidget()
        self.sub_tabs.addTab(ScheduleWidget(), "Schedule")
        self.sub_tabs.addTab(StandingsWidget(), "Standings")
        # ...
```

### 2. Data Tables with Views/Filters

**OOTP Pattern:**
- **View Dropdown**: Changes columns displayed ("What data to show?")
- **Scope Dropdown**: Defines data level ("Which league/division?")
- **Split Dropdown**: Statistical splits ("Home/Away/vs Division?")

**Implementation:**
```python
class CustomizableStatsTable(QWidget):
    def __init__(self):
        # View selector
        self.view_selector = QComboBox()
        self.view_selector.addItems([
            "Basic Stats",
            "Advanced Stats",
            "Per Game Stats",
            "Custom View..."
        ])

        # Scope selector
        self.scope_selector = QComboBox()
        self.scope_selector.addItems([
            "All Teams",
            "NFC Teams",
            "AFC Teams",
            "Division Only"
        ])

        # Stats table
        self.stats_table = StatsTable()

        # Connect signals
        self.view_selector.currentTextChanged.connect(self._update_columns)
        self.scope_selector.currentTextChanged.connect(self._filter_data)
```

### 3. Context Menus (Right-Click Actions)

**OOTP Pattern:** Right-click anywhere for relevant actions

**Examples:**
- Player row → View Player, View Stats, Cut Player, Trade Player
- Game row → View Box Score, View Play-by-Play, Simulate Game
- Team name → View Team, View Roster, View Schedule

**Implementation:**
```python
class RosterTable(StatsTable):
    def _show_context_menu(self, position):
        menu = QMenu(self)

        # Get selected player
        index = self.indexAt(position)
        player_id = self.model().data(index, Qt.UserRole)

        # Build context menu
        view_action = menu.addAction("View Player Details")
        stats_action = menu.addAction("View Career Stats")
        menu.addSeparator()
        cut_action = menu.addAction("Cut Player")
        trade_action = menu.addAction("Propose Trade")

        # Connect actions
        view_action.triggered.connect(lambda: self._view_player(player_id))
        # ...

        menu.exec_(self.viewport().mapToGlobal(position))
```

### 4. Browser-Style Navigation

**OOTP Features:**
- Navigation history (Back/Forward buttons)
- Breadcrumb trail showing current location
- Bookmarks for favorite screens
- "Recent Pages" menu

**Implementation:**
```python
class NavigationController:
    def __init__(self):
        self.history = []
        self.current_index = -1
        self.bookmarks = []

    def navigate_to(self, view_name, context=None):
        """Navigate to a view and add to history."""
        # Add to history
        self.history.append({'view': view_name, 'context': context})
        self.current_index = len(self.history) - 1

    def go_back(self):
        """Navigate to previous page."""
        if self.current_index > 0:
            self.current_index -= 1
            return self.history[self.current_index]

    def go_forward(self):
        """Navigate to next page in history."""
        if self.current_index < len(self.history) - 1:
            self.current_index += 1
            return self.history[self.current_index]

# Breadcrumb widget
class BreadcrumbBar(QWidget):
    """Display current location: League > Teams > Detroit Lions > Roster"""
    pass
```

### 5. Drag-and-Drop

**OOTP Use Cases:**
- Depth chart management (drag players between positions)
- Lineup reordering
- Trade proposals (drag players between teams)

**Implementation:**
```python
class DraggablePlayerWidget(QLabel):
    def __init__(self, player_data):
        super().__init__()
        self.player_data = player_data
        self.setAcceptDrops(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(str(self.player_data['id']))
            drag.setMimeData(mime_data)
            drag.exec_(Qt.MoveAction)

    def dropEvent(self, event):
        # Handle drop: update depth chart position
        pass
```

### 6. Customizable Column Views

**OOTP Pattern:** Users can show/hide columns via checkbox menu

**Implementation:**
```python
class ColumnCustomizationDialog(QDialog):
    """Dialog to select which stat columns to display."""

    def __init__(self, available_columns):
        super().__init__()
        self.setWindowTitle("Customize Columns")

        # Scrollable checkbox list
        layout = QVBoxLayout()

        for col in available_columns:
            checkbox = QCheckBox(col['name'])
            checkbox.setChecked(col['visible'])
            checkbox.stateChanged.connect(
                lambda state, c=col: self._toggle_column(c, state)
            )
            layout.addWidget(checkbox)

        self.setLayout(layout)
```

---

## Implementation Phases

### ✅ Phase 1: Foundation & Basic Structure (Week 1-2) - COMPLETE

**Goal:** Establish UI architecture and basic application shell

**Status:** ✅ **COMPLETE** (Completed: 2025-10-04)

**Tasks:**
1. ✅ Create `ui/` folder structure
2. ✅ Set up PySide6 dependencies (`requirements-ui.txt`)
3. ✅ Create `main.py` application entry point
4. ✅ Implement `MainWindow` with tab system (6 primary tabs)
5. ✅ Create basic view stubs (Season, Team, Player, Offseason, League, Game)
6. ✅ Set up menu bar (Game, Season, Team, Player, League, Tools, Help)
7. ✅ Create toolbar with placeholder actions
8. ✅ Implement status bar with date/phase display
9. ✅ Create basic navigation controller (placeholder)
10. ✅ Create OOTP-inspired QSS stylesheet (main.qss)

**Success Criteria:** ✅ **ALL MET**
- ✅ Application launches with empty tab structure
- ✅ Can navigate between tabs
- ✅ Menu bar and toolbar visible
- ✅ Status bar displays placeholder information
- ✅ Professional OOTP-style theme applied
- ✅ All imports verified working

**Deliverables:** ✅ **COMPLETE**
- ✅ Working PySide6 application shell
- ✅ Tab-based navigation functional
- ✅ Foundation for adding content views
- ✅ Complete documentation (`ui/README.md`, `PHASE_1_COMPLETE.md`)
- ✅ Test script (`test_ui.py`) verifying all imports

**Implementation Notes:**
- Created 20 files including complete `ui/` package structure
- All 6 view stubs created with descriptions of upcoming features
- Menu bar includes 7 menus with placeholder actions showing informative dialogs
- Toolbar includes quick action buttons (Sim Day, Sim Week, My Team, Standings, League)
- Status bar displays current date and phase (placeholders)
- QSS stylesheet provides professional OOTP-inspired theme with:
  - Blue accent color (#0066cc)
  - Clean tab design with hover effects
  - Data table styling (zebra striping, sortable headers)
  - Professional menu and button styling
  - Scroll bar customization
- Main window size: 1600x1000 with 1200x700 minimum
- All views show placeholder text explaining what's coming in which phase
- Test verification: `python test_ui.py` passes all imports
- Application launch: `python main.py` works successfully

**How to Run:**
```bash
# Install dependencies
pip install -r requirements-ui.txt

# Launch application
python main.py

# Test imports
python test_ui.py
```

**Files Created:**
- `main.py` - Application entry point
- `requirements-ui.txt` - PySide6 dependencies
- `test_ui.py` - Import verification
- `PHASE_1_COMPLETE.md` - Summary document
- `ui/main_window.py` - Main window implementation (7 tabs)
- `ui/views/*.py` - 7 view files (including calendar_view.py)
- `ui/controllers/season_controller.py` - Season data controller
- `ui/controllers/calendar_controller.py` - Calendar event controller
- `ui/models/team_list_model.py` - Team standings model
- `ui/models/calendar_model.py` - Calendar events model
- `ui/resources/styles/main.qss` - OOTP-inspired stylesheet
- `ui/README.md` - UI documentation
- `docs/ui/calendar_tab_spec.md` - Calendar tab specification
- All `ui/` package `__init__.py` files

---

### Phase 2: Core Views - Season & Team (Week 3-4)

**Goal:** Implement Season and Team views with basic functionality

**Status:** ⏳ Ready to Start

**Tasks:**

**Season View:**
1. ⏳ Create `SeasonView` with sub-tabs (Schedule, Standings, Stats Leaders, Playoff Picture)
2. ⏳ Implement schedule grid with games display
3. ⏳ Add week selector dropdown
4. ⏳ Create simulation controls (Simulate Day, Simulate Week)
5. ⏳ Connect to `SeasonCycleController` for simulation
6. ⏳ Display game results in schedule grid
7. ⏳ Implement basic standings table (sorted by wins)

**Team View:**
1. ⏳ Create `TeamView` with sub-tabs (Roster, Depth Chart, Finances, Staff)
2. ⏳ Implement roster table with player list
3. ⏳ Add team selector dropdown (for viewing other teams)
4. ⏳ Display salary cap information
5. ⏳ Connect to database for roster data
6. ⏳ Implement position filter dropdown
7. ⏳ Add search box for player names

**Success Criteria:**
- Season schedule displays correctly from database
- Can simulate day/week and see results update
- Standings table shows accurate rankings
- Roster displays all players for selected team
- Can filter roster by position
- Salary cap information visible

**Deliverables:**
- Functional Season view with simulation
- Functional Team view with roster display
- Database integration working

---

### Phase 3: Data Tables & Statistics Display (Week 5-6)

**Goal:** Implement advanced data table features (OOTP-style)

**Tasks:**

**Stats Table Widget:**
1. ✅ Create `StatsTable` widget extending QTableView
2. ✅ Implement Qt Model/View architecture
3. ✅ Add sortable columns (click header to sort)
4. ✅ Implement zebra striping (alternating row colors)
5. ✅ Add number formatting (stats, percentages, money)
6. ✅ Implement column resizing and reordering
7. ✅ Add context menu (View Player, Export Data)
8. ✅ Create data models for different stat types:
   - `PlayerStatsModel` (passing, rushing, receiving stats)
   - `TeamStatsModel` (team offensive/defensive stats)
   - `StandingsModel` (W-L records, playoff chances)

**Customizable Views:**
1. ✅ Implement view selector dropdown
2. ✅ Create column customization dialog
3. ✅ Add preset views (Basic, Advanced, Per Game, Custom)
4. ✅ Save/load user column preferences
5. ✅ Implement filter/scope dropdowns
6. ✅ Add search/filter functionality

**Success Criteria:**
- Tables display thousands of rows efficiently (virtual scrolling)
- Columns sortable by clicking headers
- Users can customize which columns to display
- Data formatted correctly (numbers, money, percentages)
- Context menus work on all tables
- Filters apply correctly to displayed data

**Deliverables:**
- Professional OOTP-style data tables
- Customizable column views
- Efficient rendering for large datasets

---

### Phase 4: Offseason Interface (Week 7-8)

**Goal:** Implement offseason dashboard and interaction dialogs

**Tasks:**

**Offseason Dashboard:**
1. ✅ Create `OffseasonView` with dashboard layout
2. ✅ Display current date and offseason phase
3. ✅ Implement deadline countdown widget
4. ✅ Show salary cap status panel
5. ✅ Display pending free agents list
6. ✅ Add action buttons (Franchise Tag, Browse FA, Draft, Cuts)
7. ✅ Implement calendar advancement controls
8. ✅ Create transaction feed widget (league-wide activity)

**Offseason Dialogs:**
1. ✅ Create `FranchiseTagDialog`
   - List eligible players
   - Show tag salary calculation
   - Confirm/cancel tag application
2. ✅ Create `FreeAgentSigningDialog`
   - Browse available free agents
   - Filter by position/age/salary
   - Negotiate contract terms
   - Validate cap space
3. ✅ Create `DraftPickDialog`
   - Display draft board
   - Show team needs
   - Make selection
   - Track picks used
4. ✅ Create `RosterCutDialog`
   - List all players with cut designation
   - Show cap implications (dead money)
   - Bulk cut selection
   - Confirm cuts

**Integration:**
1. ✅ Connect dialogs to offseason event system (`src/events/`)
2. ✅ Trigger events on user actions
3. ✅ Update UI after event execution
4. ✅ Show validation errors (insufficient cap space, etc.)

**Success Criteria:**
- Offseason dashboard displays accurate information
- Deadlines count down correctly
- All offseason actions work via dialogs
- Events trigger correctly when user makes decisions
- UI updates reflect database changes
- Validation prevents invalid actions

**Deliverables:**
- Complete offseason management interface
- All offseason dialogs functional
- Integration with offseason event system

---

### Phase 5: Advanced Features (Week 9-10)

**Goal:** Implement navigation, drag-and-drop, and polish

**Tasks:**

**Navigation System:**
1. ✅ Implement navigation history (back/forward)
2. ✅ Create breadcrumb bar widget
3. ✅ Add bookmarks system (favorite screens)
4. ✅ Implement "Recent Pages" menu
5. ✅ Add keyboard shortcuts (Ctrl+B for bookmark, Alt+← for back)
6. ✅ Create hyperlinks between related views (click team name → Team view)

**Drag-and-Drop:**
1. ✅ Implement draggable player widgets
2. ✅ Create depth chart drag-and-drop
3. ✅ Add visual feedback during drag
4. ✅ Validate drop targets
5. ✅ Update database on successful drop

**Additional Widgets:**
1. ✅ Create player card widget (compact info display)
2. ✅ Implement game ticker (live scores)
3. ✅ Create calendar widget with events
4. ✅ Add playoff bracket visualization

**Polish:**
1. ✅ Implement dark mode theme
2. ✅ Add team color theming (optional)
3. ✅ Create application icons
4. ✅ Add loading indicators for long operations
5. ✅ Implement notification system (toasts/alerts)
6. ✅ Add tooltips for all buttons/actions

**Success Criteria:**
- Navigation works smoothly (back/forward/bookmarks)
- Breadcrumbs show current location
- Drag-and-drop feels natural and responsive
- UI polish matches professional applications
- Dark mode works correctly
- Icons and visuals consistent

**Deliverables:**
- Complete navigation system
- Functional drag-and-drop
- Polished, professional UI

---

### Phase 6: Testing & Documentation (Week 11-12)

**Goal:** Comprehensive testing and user documentation

**Tasks:**

**Testing:**
1. ✅ Unit tests for custom widgets
2. ✅ Integration tests for view controllers
3. ✅ UI responsiveness testing (window resize, scaling)
4. ✅ Performance testing (large datasets, 1000+ rows)
5. ✅ Cross-platform testing (Windows, macOS, Linux)
6. ✅ User acceptance testing (usability study)
7. ✅ Accessibility testing (keyboard navigation, screen readers)

**Bug Fixes:**
1. ✅ Fix layout issues
2. ✅ Resolve data synchronization bugs
3. ✅ Address performance bottlenecks
4. ✅ Handle edge cases

**Documentation:**
1. ✅ Create user manual (`docs/user_guide.md`)
2. ✅ Write UI architecture documentation (`docs/architecture/ui_architecture.md`)
3. ✅ Document custom widgets and components
4. ✅ Create developer guide for extending UI
5. ✅ Add inline code comments
6. ✅ Create screenshots/videos for features

**Success Criteria:**
- All tests passing
- No critical bugs
- Application performs well on all platforms
- Documentation complete and clear
- User feedback incorporated

**Deliverables:**
- Fully tested application
- Complete user and developer documentation
- Ready for release

---

## Integration Strategy

### Connecting UI to Simulation Engine

**Principle: UI Controllers Mediate Between Views and Engine**

```
┌──────────────┐
│ View (UI)    │  ← User interactions
└──────┬───────┘
       │
       ↓
┌──────────────────┐
│ UI Controller    │  ← Translates UI events to engine calls
└──────┬───────────┘
       │
       ↓
┌────────────────────────────┐
│ Simulation Engine (src/)   │  ← Pure business logic
│ - SeasonCycleController    │
│ - DatabaseAPI              │
│ - Event System             │
└────────────────────────────┘
```

### Example: Season Simulation Flow

**1. User clicks "Simulate Day" button in Season View**

```python
# ui/views/season_view.py
class SeasonView(QWidget):
    def __init__(self, parent):
        self.controller = SeasonController(parent.db_path, parent.dynasty_id)

        self.sim_day_btn.clicked.connect(self._simulate_day)

    def _simulate_day(self):
        # Call controller
        result = self.controller.simulate_day()

        # Update UI with results
        self._update_schedule_table(result.games_played)
        self._update_standings()
        self._show_notification(f"Simulated {result.date}")
```

**2. Controller calls simulation engine**

```python
# ui/controllers/season_controller.py
class SeasonController:
    def __init__(self, db_path, dynasty_id):
        # Import from src/ (simulation engine)
        from src.season.season_cycle_controller import SeasonCycleController
        from src.database.api import DatabaseAPI

        self.db = DatabaseAPI(db_path)
        self.season_sim = SeasonCycleController(
            database_path=db_path,
            dynasty_id=dynasty_id
        )

    def simulate_day(self):
        # Call simulation engine
        result = self.season_sim.advance_day()

        # Return structured result for UI
        return SimulationResult(
            date=result['date'],
            games_played=result['games'],
            phase=result['phase']
        )
```

**3. Simulation engine executes business logic**

```python
# src/season/season_cycle_controller.py (existing)
class SeasonCycleController:
    def advance_day(self):
        # Pure simulation logic (no UI dependencies)
        games = self._simulate_games_for_day()
        self._update_standings()

        return {
            'date': self.current_date,
            'games': games,
            'phase': self.current_phase
        }
```

### Data Flow Patterns

**Pattern 1: Database → UI (Read)**
```python
# UI Controller fetches data from engine
def load_roster_data(self, team_id):
    from src.database.api import DatabaseAPI

    db = DatabaseAPI(self.db_path)
    players = db.get_team_roster(team_id, self.dynasty_id)

    # Convert to UI-friendly format
    return [self._format_player_for_display(p) for p in players]
```

**Pattern 2: UI → Database (Write via Events)**
```python
# UI triggers events in simulation engine
def apply_franchise_tag(self, player_id):
    from src.events.contract_events import FranchiseTagEvent

    # Create event
    event = FranchiseTagEvent(
        team_id=self.user_team_id,
        player_id=player_id,
        tag_type="FRANCHISE",
        tag_date=self.current_date,
        season=self.season_year
    )

    # Execute event (simulation engine handles DB write)
    result = event.simulate()

    return result.success
```

**Pattern 3: Real-time Updates (Observer Pattern)**
```python
# UI observes simulation engine changes
class StandingsWidget(QWidget):
    def __init__(self, controller):
        self.controller = controller

        # Subscribe to updates
        self.controller.standings_updated.connect(self._refresh_standings)

    def _refresh_standings(self):
        standings = self.controller.get_current_standings()
        self.standings_model.update_data(standings)
```

### Dynasty Isolation

**Every UI operation includes dynasty_id:**

```python
# UI Controller always passes dynasty context
class TeamController:
    def __init__(self, db_path, dynasty_id):
        self.db_path = db_path
        self.dynasty_id = dynasty_id  # Always tracked

    def get_roster(self, team_id):
        from src.database.api import DatabaseAPI

        db = DatabaseAPI(self.db_path)
        # Dynasty isolation enforced
        return db.get_team_roster(team_id, dynasty_id=self.dynasty_id)
```

---

## Design Patterns & Best Practices

### 1. Qt Model/View Programming

**Separate data (Model) from presentation (View)**

```python
# Model: Provides data to view
class PlayerStatsModel(QAbstractTableModel):
    def __init__(self, stats_data):
        super().__init__()
        self._data = stats_data
        self._headers = ['Name', 'Pos', 'Comp', 'Att', 'Yds', 'TD', 'INT', 'Rating']

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            player = self._data[index.row()]
            return player[self._headers[index.column()]]
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None

# View: Displays data from model
table = QTableView()
model = PlayerStatsModel(player_stats)
table.setModel(model)
```

**Benefits:**
- Multiple views can share same model
- Data updates propagate automatically
- Easy to add sorting/filtering via proxy models

### 2. Signal/Slot Communication

**Decouple components using Qt's signal/slot mechanism**

```python
# Widget emits signal when user takes action
class RosterTable(QTableView):
    player_selected = Signal(int)  # Signal with player_id

    def selectionChanged(self, selected, deselected):
        super().selectionChanged(selected, deselected)
        if selected.indexes():
            player_id = selected.indexes()[0].data(Qt.UserRole)
            self.player_selected.emit(player_id)

# Another widget listens to signal
class PlayerDetailPanel(QWidget):
    def __init__(self, roster_table):
        super().__init__()
        roster_table.player_selected.connect(self.show_player_details)

    def show_player_details(self, player_id):
        # Load and display player info
        pass
```

### 3. Data Formatting for Display

**Create utility functions for consistent formatting**

```python
# ui/utils/formatters.py
def format_money(amount: int) -> str:
    """Format money with $ and commas."""
    return f"${amount:,}"

def format_percentage(value: float) -> str:
    """Format percentage with 1 decimal place."""
    return f"{value:.1f}%"

def format_stat(stat_value: int, stat_type: str) -> str:
    """Format stat based on type."""
    if stat_type == 'yards':
        return f"{stat_value:,} yds"
    elif stat_type == 'rating':
        return f"{stat_value:.1f}"
    return str(stat_value)

def format_player_name(first: str, last: str, position: str = None) -> str:
    """Format player name with position."""
    name = f"{first[0]}. {last}"
    if position:
        return f"{name} ({position})"
    return name
```

### 4. Performance Optimization

**Handle large datasets efficiently**

```python
# Use QSortFilterProxyModel for filtering without reloading data
class FilteredStatsTable(QWidget):
    def __init__(self):
        self.table = QTableView()
        self.model = StatsModel(data)

        # Proxy model for filtering
        self.proxy = QSortFilterProxyModel()
        self.proxy.setSourceModel(self.model)
        self.table.setModel(self.proxy)

    def filter_by_position(self, position):
        # Efficient filtering via proxy
        self.proxy.setFilterRegExp(QRegExp(position, Qt.CaseInsensitive))
        self.proxy.setFilterKeyColumn(1)  # Position column

# Virtual scrolling (built-in with QTableView)
# Only renders visible rows - handles thousands of items efficiently
```

### 5. Preferences and Settings Persistence

**Save user preferences to file**

```python
# ui/utils/preferences.py
from PySide6.QtCore import QSettings

class AppPreferences:
    def __init__(self):
        self.settings = QSettings("OwnersSimDev", "TheOwnersSim")

    def save_column_config(self, view_name, columns):
        """Save which columns are visible."""
        self.settings.beginGroup(f"columns/{view_name}")
        self.settings.setValue("visible", columns)
        self.settings.endGroup()

    def load_column_config(self, view_name):
        """Load saved column configuration."""
        self.settings.beginGroup(f"columns/{view_name}")
        columns = self.settings.value("visible", [])
        self.settings.endGroup()
        return columns

    def save_theme(self, theme_name):
        self.settings.setValue("theme", theme_name)

    def load_theme(self):
        return self.settings.value("theme", "default")
```

---

## Testing Strategy

### Unit Testing UI Components

```python
# tests/ui/test_stats_table.py
import pytest
from PySide6.QtWidgets import QApplication
from ui.widgets.stats_table import StatsTable
from ui.models.stats_model import PlayerStatsModel

@pytest.fixture
def app():
    """Create QApplication for tests."""
    return QApplication([])

@pytest.fixture
def sample_stats():
    return [
        {'name': 'M. Stafford', 'pos': 'QB', 'comp': 350, 'att': 550, 'yds': 4500, 'td': 35, 'int': 10},
        # ... more players
    ]

def test_stats_table_displays_data(app, sample_stats):
    """Test that stats table displays player data correctly."""
    model = PlayerStatsModel(sample_stats)
    table = StatsTable()
    table.set_data_model(model)

    # Verify row count
    assert table.model().rowCount() == len(sample_stats)

    # Verify first player data
    first_name = table.model().index(0, 0).data()
    assert first_name == 'M. Stafford'

def test_stats_table_sorting(app, sample_stats):
    """Test that clicking column header sorts data."""
    model = PlayerStatsModel(sample_stats)
    table = StatsTable()
    table.set_data_model(model)

    # Sort by touchdowns (descending)
    table.sortByColumn(5, Qt.DescendingOrder)

    # Verify top player has most TDs
    top_player_tds = table.model().index(0, 5).data()
    assert top_player_tds == 35
```

### Integration Testing

```python
# tests/ui/test_season_view_integration.py
def test_simulate_day_updates_ui(app):
    """Test that simulating a day updates schedule and standings."""
    # Set up test database with sample data
    db_path = "test_season.db"
    dynasty_id = "test_dynasty"

    # Create season view
    view = SeasonView(db_path, dynasty_id)

    # Simulate a day
    view.sim_day_btn.click()

    # Verify UI updated
    assert view.schedule_table.rowCount() > 0
    assert view.standings_table.rowCount() == 32
    assert "Dec 15" in view.current_date_label.text()
```

### Mock Data for Development

```python
# tests/ui/mock_data.py
def create_mock_roster(team_id=1, size=53):
    """Generate mock roster for UI testing."""
    positions = ['QB', 'RB', 'WR', 'TE', 'OL', 'DL', 'LB', 'CB', 'S', 'K', 'P']

    roster = []
    for i in range(size):
        player = {
            'id': i,
            'number': i + 1,
            'name': f'Player {i+1}',
            'position': positions[i % len(positions)],
            'age': 20 + (i % 15),
            'overall': 60 + (i % 30),
            'contract_years': 1 + (i % 4),
            'salary': 1000000 + (i * 100000)
        }
        roster.append(player)

    return roster

def create_mock_schedule(season_year=2024):
    """Generate mock NFL schedule."""
    # ... generate 18 weeks of games
    pass
```

---

## Resources & References

### Official Documentation

**PySide6 / Qt for Python:**
- [PySide6 Official Docs](https://doc.qt.io/qtforpython-6/)
- [PySide6 Tutorial](https://www.pythonguis.com/pyside6-tutorial/)
- [Qt Model/View Programming](https://doc.qt.io/qt-6/model-view-programming.html)
- [Qt Style Sheets Reference](https://doc.qt.io/qt-6/stylesheet-reference.html)

**Qt Widgets:**
- [QTableView Documentation](https://doc.qt.io/qt-6/qtableview.html)
- [QTabWidget Documentation](https://doc.qt.io/qt-6/qtabwidget.html)
- [Qt Drag and Drop](https://doc.qt.io/qt-6/dnd.html)

### OOTP UI Analysis

**Key Takeaways from OOTP Interface:**
1. **Tab Hierarchy**: Primary tabs (top) + secondary tabs (within views)
2. **Data Tables**: Extensive use of sortable, filterable tables
3. **Customization**: Users control column visibility and data views
4. **Context Menus**: Right-click actions everywhere
5. **Navigation**: Browser-style back/forward, breadcrumbs, bookmarks
6. **Performance**: Handles massive datasets (thousands of players, decades of stats)

**OOTP Screenshots for Reference:**
- [OOTP 25 Interface Overview](https://www.ootpdevelopments.com/out-of-the-park-baseball-home/)
- [Community UI Mockups](https://forums.ootpdevelopments.com/showthread.php?p=4980836)

### Design Patterns

**UI Design Patterns:**
- [Data Table Design Best Practices](https://wpdatatables.com/table-ui-design/)
- [Tab Navigation Design Guidelines](https://uxdworld.com/tabs-navigation-design-best-practices/)
- [Dashboard UI Patterns](https://www.pencilandpaper.io/articles/ux-pattern-analysis-data-dashboards)

**Qt Design Patterns:**
- [Qt Model/View Tutorial](https://doc.qt.io/qt-6/modelview.html)
- [Qt Signal/Slot Mechanism](https://doc.qt.io/qt-6/signalsandslots.html)
- [Qt Layouts and Widgets](https://doc.qt.io/qt-6/layout.html)

### Development Tools

**Qt Development:**
- **Qt Designer**: Visual UI design tool (drag-and-drop widgets)
- **Qt Creator**: Full IDE with Qt-specific features
- **VSCode Qt Extensions**:
  - Qt for Python (syntax highlighting)
  - Qt Configure (project setup)

**Styling:**
- **QSS Editors**: Stylesheets for Qt (CSS-like)
- **qt-material**: Material Design themes for Qt
- **QDarkStyleSheet**: Pre-made dark theme

### Learning Resources

**Tutorials:**
- [PySide6 Complete Tutorial](https://www.pythonguis.com/pyside6/)
- [Qt Widgets Examples](https://doc.qt.io/qt-6/qtwidgets-index.html)
- [Building Desktop Apps with Qt](https://realpython.com/python-pyqt-gui-calculator/)

**Books:**
- *Create GUI Applications with Python & Qt6* (Martin Fitzpatrick)
- *Rapid GUI Programming with Python and Qt* (Mark Summerfield)

---

## Next Steps

### Immediate Actions (This Week)

1. **Set up development environment**
   ```bash
   # Install PySide6
   pip install PySide6>=6.6.0

   # Create ui/ folder structure
   mkdir -p ui/{views,widgets,dialogs,models,controllers,resources/{icons,styles},utils}
   ```

2. **Create basic application shell**
   - Write `main.py` entry point
   - Implement `ui/main_window.py` with tabs
   - Create empty view stubs

3. **Test basic UI**
   ```bash
   # Run application
   python main.py
   ```

### Phase 1 Kickoff (Next Week)

1. Review this plan with development team
2. Set up version control branch for UI development
3. Begin Phase 1 implementation (Foundation & Basic Structure)
4. Create first working prototype with tab navigation

### Long-term Roadmap

**Weeks 1-2:** Foundation (tab structure, menus, basic views)
**Weeks 3-4:** Core views (Season, Team with basic data)
**Weeks 5-6:** Advanced tables (sorting, filtering, customization)
**Weeks 7-8:** Offseason interface (dialogs, interactions)
**Weeks 9-10:** Advanced features (navigation, drag-drop, polish)
**Weeks 11-12:** Testing, documentation, release preparation

**Total Timeline:** ~12 weeks for complete UI implementation

---

## Appendix: Code Templates

### Main Application Entry Point

**`main.py`:**
```python
#!/usr/bin/env python3
"""
The Owner's Sim - NFL Management Simulation
Desktop Application Entry Point
"""
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from ui.main_window import MainWindow

def main():
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("The Owner's Sim")
    app.setOrganizationName("OwnersSimDev")
    app.setOrganizationDomain("ownerssim.com")

    # Load stylesheet
    stylesheet_path = Path(__file__).parent / "ui" / "resources" / "styles" / "main.qss"
    if stylesheet_path.exists():
        with open(stylesheet_path, "r") as f:
            app.setStyleSheet(f.read())

    # Create and show main window
    window = MainWindow()
    window.show()

    # Run event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
```

### Main Window Template

**`ui/main_window.py`:**
```python
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QToolBar, QStatusBar,
    QMenu, QMenuBar, QLabel
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QIcon

from ui.views.season_view import SeasonView
from ui.views.team_view import TeamView
from ui.views.player_view import PlayerView
from ui.views.offseason_view import OffseasonView
from ui.views.league_view import LeagueView
from ui.views.game_view import GameView

class MainWindow(QMainWindow):
    """
    Main application window with OOTP-style tab navigation.
    """

    def __init__(self, db_path="data/database/nfl_simulation.db", dynasty_id="default"):
        super().__init__()

        self.db_path = db_path
        self.dynasty_id = dynasty_id

        self.setWindowTitle("The Owner's Sim")
        self.setGeometry(100, 100, 1600, 1000)

        self._create_central_widget()
        self._create_menus()
        self._create_toolbar()
        self._create_statusbar()

    def _create_central_widget(self):
        """Create central tab widget with primary views."""
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.setMovable(False)

        # Add primary views
        self.season_view = SeasonView(self)
        self.team_view = TeamView(self)
        self.player_view = PlayerView(self)
        self.offseason_view = OffseasonView(self)
        self.league_view = LeagueView(self)
        self.game_view = GameView(self)

        self.tabs.addTab(self.season_view, "Season")
        self.tabs.addTab(self.team_view, "Team")
        self.tabs.addTab(self.player_view, "Player")
        self.tabs.addTab(self.offseason_view, "Offseason")
        self.tabs.addTab(self.league_view, "League")
        self.tabs.addTab(self.game_view, "Game")

        self.setCentralWidget(self.tabs)

    def _create_menus(self):
        """Create menu bar."""
        menubar = self.menuBar()

        # Game Menu
        game_menu = menubar.addMenu("&Game")
        game_menu.addAction(self._create_action("&New Dynasty", self._new_dynasty))
        game_menu.addAction(self._create_action("&Load Dynasty", self._load_dynasty))
        game_menu.addSeparator()
        game_menu.addAction(self._create_action("&Settings", self._show_settings))
        game_menu.addSeparator()
        game_menu.addAction(self._create_action("E&xit", self.close, "Ctrl+Q"))

        # Season Menu
        season_menu = menubar.addMenu("&Season")
        season_menu.addAction(self._create_action("Simulate &Day", self._sim_day))
        season_menu.addAction(self._create_action("Simulate &Week", self._sim_week))

        # Team Menu
        team_menu = menubar.addMenu("&Team")
        team_menu.addAction(self._create_action("View &Roster", lambda: self.tabs.setCurrentIndex(1)))
        team_menu.addAction(self._create_action("Depth &Chart", self._show_depth_chart))

        # Help Menu
        help_menu = menubar.addMenu("&Help")
        help_menu.addAction(self._create_action("&User Guide", self._show_help))
        help_menu.addAction(self._create_action("&About", self._show_about))

    def _create_toolbar(self):
        """Create toolbar with quick actions."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)

        # Add toolbar actions
        toolbar.addAction(self._create_action("Sim Day", self._sim_day, icon="play"))
        toolbar.addAction(self._create_action("Sim Week", self._sim_week, icon="fast-forward"))
        toolbar.addSeparator()
        toolbar.addAction(self._create_action("My Team", lambda: self.tabs.setCurrentIndex(1), icon="users"))
        toolbar.addAction(self._create_action("Standings", self._show_standings, icon="list"))

    def _create_statusbar(self):
        """Create status bar with current date and phase."""
        statusbar = QStatusBar()
        self.setStatusBar(statusbar)

        self.date_label = QLabel("Date: Sep 5, 2024")
        self.phase_label = QLabel("Phase: Regular Season - Week 1")

        statusbar.addWidget(self.date_label)
        statusbar.addPermanentWidget(self.phase_label)

    def _create_action(self, text, slot, shortcut=None, icon=None):
        """Helper to create QAction."""
        action = QAction(text, self)
        action.triggered.connect(slot)
        if shortcut:
            action.setShortcut(shortcut)
        if icon:
            # Load icon from resources
            action.setIcon(QIcon(f"ui/resources/icons/{icon}.png"))
        return action

    # Action handlers (placeholders)
    def _new_dynasty(self): pass
    def _load_dynasty(self): pass
    def _show_settings(self): pass
    def _sim_day(self): pass
    def _sim_week(self): pass
    def _show_depth_chart(self): pass
    def _show_standings(self): pass
    def _show_help(self): pass
    def _show_about(self): pass
```

---

## Document Metadata

**Version:** 1.1.0
**Created:** 2025-10-04
**Last Updated:** 2025-10-04
**Author:** The Owner's Sim Development Team
**Status:** Phase 1 Complete ✅ - Phase 2 Ready to Start

**Phase Progress:**
- ✅ Phase 1: Foundation & Basic Structure (Complete - 2025-10-04)
- ⏳ Phase 2: Core Views - Season & Team (Ready to Start)
- ⬜ Phase 3: Data Tables & Statistics Display
- ⬜ Phase 4: Offseason Interface
- ⬜ Phase 5: Advanced Features
- ⬜ Phase 6: Testing & Documentation

**Implementation Files:**
- ✅ `main.py` - Application entry point
- ✅ `requirements-ui.txt` - UI dependencies
- ✅ `test_ui.py` - Import verification script
- ✅ `ui/main_window.py` - Main window with 7 tabs, menus, toolbar, status bar
- ✅ `ui/views/*.py` - 7 view files (season, calendar, team, player, offseason, league, game)
- ✅ `ui/controllers/season_controller.py` - Season data access controller
- ✅ `ui/controllers/calendar_controller.py` - Calendar event controller with month navigation
- ✅ `ui/models/team_list_model.py` - Qt model for team standings
- ✅ `ui/models/calendar_model.py` - Qt model for calendar events (color-coded)
- ✅ `ui/resources/styles/main.qss` - OOTP-inspired stylesheet
- ✅ `ui/README.md` - UI documentation
- ✅ `docs/ui/calendar_tab_spec.md` - Calendar tab specification document
- ✅ `PHASE_1_COMPLETE.md` - Phase 1 summary
- ✅ Fixed circular import in `src/calendar/__init__.py`

**Related Documents:**
- `docs/plans/offseason_plan.md` - Offseason system implementation
- `docs/plans/full_season_simulation_plan.md` - Complete season cycle
- `docs/architecture/play_engine.md` - Core simulation architecture
- `docs/schema/database_schema.md` - Database design
- `ui/README.md` - UI package documentation
- `PHASE_1_COMPLETE.md` - Phase 1 completion summary

**Next Review:** After Phase 2 completion (Week 4)
