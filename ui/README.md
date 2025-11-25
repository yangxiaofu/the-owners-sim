# The Owner's Sim - Desktop UI

OOTP-inspired desktop user interface for The Owner's Sim NFL management simulation.

## Quick Start

### 1. Install Dependencies

```bash
# Install PySide6 and UI dependencies
pip install -r requirements-ui.txt
```

### 2. Run the Application

```bash
# From project root
python main.py
```

## Current Status (Phase 1 Complete)

✅ **Foundation Complete**
- Application shell with tab-based navigation
- 6 primary tabs: Season, Team, Player, Offseason, League, Game
- Menu bar with Game, Season, Team, Player, League, Tools, Help menus
- Toolbar with quick actions
- Status bar showing date and phase
- OOTP-inspired QSS stylesheet

## UI Structure

```
ui/
├── main_window.py          # Main application window
├── views/                  # Tab content views
│   ├── season_view.py     # Season overview (Phase 2)
│   ├── team_view.py       # Team management (Phase 2)
│   ├── player_view.py     # Player details (Phase 3)
│   ├── offseason_view.py  # Offseason dashboard (Phase 4)
│   ├── league_view.py     # League stats (Phase 3)
│   └── game_view.py       # Live game simulation (Phase 2)
├── widgets/               # Reusable custom widgets (Phase 3+)
├── dialogs/               # Modal dialogs (Phase 4+)
├── models/                # Qt data models (Phase 3+)
├── controllers/           # UI controllers (Phase 2+)
├── resources/
│   └── styles/
│       └── main.qss       # Application stylesheet
└── utils/                 # UI utilities (Phase 3+)
```

## Features Implemented

### Main Window
- **Tab Navigation**: OOTP-style tabs for primary sections
- **Menu Bar**: Complete menu structure with placeholders
- **Toolbar**: Quick action buttons
- **Status Bar**: Current date and phase display
- **Styling**: Professional OOTP-inspired theme

### Views (Placeholders)
All views show what's coming in future phases:
- Season View → Phase 2
- Team View → Phase 2
- Player View → Phase 3
- Offseason View → Phase 4
- League View → Phase 3
- Game View → Phase 2

## Coming in Phase 2 (Weeks 3-4)

### Season View
- Interactive schedule grid
- Week selector dropdown
- Simulation controls (Day/Week)
- Real-time standings table
- Database integration

### Team View
- Roster table with player data
- Team selector dropdown
- Position filter
- Player search
- Salary cap display

### Game View
- Live play-by-play commentary
- Scoreboard
- Player stats updates

## Coming in Phase 3 (Weeks 5-6)

### Advanced Data Tables
- Sortable columns (OOTP-style)
- Customizable column views
- Zebra striping
- Context menus
- Export functionality
- Filtering and search

### Player View
- Player information card
- Career statistics
- Contract details
- Season-by-season breakdown

### League View
- Statistical leaders
- Team rankings
- League-wide comparisons

## Coming in Phase 4 (Weeks 7-8)

### Offseason Dashboard
- Deadline countdown timers
- Salary cap status
- Pending free agents
- Action buttons (Tag, Sign, Draft, Cut)
- Transaction feed

### Offseason Dialogs
- Franchise tag selection
- Free agent signing
- Draft board
- Roster cuts

## Coming in Phase 5 (Weeks 9-10)

### Advanced Features
- Navigation system (back/forward/bookmarks)
- Breadcrumb bar
- Drag-and-drop depth chart
- Dark mode theme
- Player cards
- Game ticker

## Coming in Phase 6 (Weeks 11-12)

### Testing & Polish
- Comprehensive testing
- Performance optimization
- User documentation
- Bug fixes
- Final polish

## Development Notes

### Integration with Simulation Engine

The UI layer (`ui/`) is completely separate from the simulation engine (`src/`):

```python
# UI Controller pattern
from src.season.season_cycle_controller import SeasonCycleController
from src.database.api import DatabaseAPI

class SeasonController:
    def __init__(self, db_path, dynasty_id):
        self.db = DatabaseAPI(db_path)
        self.season_sim = SeasonCycleController(db_path, dynasty_id)

    def simulate_day(self):
        result = self.season_sim.advance_day()
        return result  # UI formats and displays
```

### Running Tests

```bash
# Test UI imports
python test_ui.py

# Run application
python main.py
```

### Customizing Styles

Edit `ui/resources/styles/main.qss` to customize the appearance. The current theme is OOTP-inspired with:
- Blue accent color (#0066cc)
- Clean tab design
- Professional data tables
- Hover effects

## Troubleshooting

### "No module named 'PySide6'"
```bash
pip install -r requirements-ui.txt
```

### "No module named 'ui'"
Make sure you're running from the project root directory.

### Application won't launch
Check that all view files exist:
```bash
ls -la ui/views/
```

## Resources

- [PySide6 Documentation](https://doc.qt.io/qtforpython-6/)
- [UI Development Plan](../docs/archive/plans/ui_development_plan.md)
- [OOTP Baseball](https://www.ootpdevelopments.com/) - Design inspiration

---

**Phase 1 Status**: ✅ Complete
**Next Phase**: Phase 2 - Core Views (Season & Team)
