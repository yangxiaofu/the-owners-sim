# Milestone 11: Schedule & Rivalries

> **Status:** COMPLETE (All 8 Tollgates complete)
> **Dependencies:** None (standalone, but enhances Game Scenarios M9)
> **Priority:** Simulation Realism

## Overview

Enhance the schedule system with realistic NFL features: rivalries, primetime games, bye weeks, special events (Thanksgiving, Christmas, international games), and rivalry-driven gameplay effects. Creates emotional stakes and strategic scheduling that mirrors the real NFL experience.

## What Already Exists

The codebase has solid schedule generation infrastructure:

- `src/game_cycle/services/nfl_schedule_generator.py` - NFL-compliant 17-game formula
  - Division games (6 per team, 2x each rival)
  - In-conference rotation (3-year cycle)
  - Cross-conference rotation (4-year cycle)
  - Same-place finisher games
  - 17th game matchups
- `src/game_cycle/database/schedule_rotation_api.py` - Rotation state persistence
- `src/game_cycle/services/schedule_service.py` - Schedule generation orchestration
- Game events already track `is_divisional` and `is_conference` flags

## What's Missing

1. **Rivalry System** - No concept of historic or divisional rivalries
2. **Primetime Scheduling** - All games scheduled same time (Sunday 1pm)
3. **Bye Weeks** - No rest weeks for teams
4. **Special Games** - No Thanksgiving, Christmas, London games
5. **Rivalry Effects** - No gameplay modifiers for rivalry games
6. **Head-to-Head History** - No tracking of all-time records between teams
7. **Flex Scheduling** - No late-season schedule adjustments

---

## Tollgate 1: Rivalry Definition System

**Goal:** Define and persist rivalry relationships between teams.

### 1.1 Rivalry Data Model

**File:** `src/game_cycle/models/rivalry.py`

```python
@dataclass
class Rivalry:
    """Represents a rivalry between two teams."""
    rivalry_id: str                    # UUID
    team_a_id: int                     # Lower team ID (for consistent ordering)
    team_b_id: int                     # Higher team ID
    rivalry_type: RivalryType          # DIVISION, HISTORIC, GEOGRAPHIC, RECENT
    rivalry_name: Optional[str]        # "Battle of Ohio", "Border War", etc.
    intensity: int                     # 1-100 scale, affects gameplay modifiers
    is_protected: bool                 # Appears annually regardless of rotation
    created_dynasty_id: Optional[str]  # If dynasty-created (playoff grudge)

class RivalryType(Enum):
    DIVISION = "division"              # Same division (automatic)
    HISTORIC = "historic"              # Classic matchups (Bears-Packers)
    GEOGRAPHIC = "geographic"          # Regional (Giants-Jets)
    RECENT = "recent"                  # Playoff history, recent close games
```

### 1.2 Static Rivalry Configuration

**File:** `src/config/rivalries.json`

```json
{
  "historic_rivalries": [
    {
      "teams": [21, 23],
      "name": "The Oldest Rivalry",
      "notes": "Bears vs Packers - NFL's oldest rivalry",
      "base_intensity": 95,
      "is_protected": true
    },
    {
      "teams": [17, 19],
      "name": "NFC East Showdown",
      "notes": "Cowboys vs Eagles",
      "base_intensity": 90,
      "is_protected": true
    }
    // ... 15-20 historic rivalries
  ],
  "geographic_rivalries": [
    {
      "teams": [18, 4],
      "name": "MetLife Rivalry",
      "notes": "Giants vs Jets - same stadium",
      "base_intensity": 75,
      "is_protected": false
    }
    // ... geographic rivalries
  ]
}
```

### 1.3 Rivalry Database API

**File:** `src/game_cycle/database/rivalry_api.py`

```python
class RivalryAPI:
    """Database operations for rivalry management."""

    def get_rivalries_for_team(dynasty_id: str, team_id: int) -> List[Rivalry]
    def get_rivalry_between_teams(dynasty_id: str, team_a: int, team_b: int) -> Optional[Rivalry]
    def get_all_rivalries(dynasty_id: str) -> List[Rivalry]
    def create_rivalry(dynasty_id: str, rivalry: Rivalry) -> None
    def update_intensity(dynasty_id: str, rivalry_id: str, intensity: int) -> None
    def initialize_rivalries(dynasty_id: str) -> int  # From config + divisions
```

### 1.4 Database Schema Addition

**File:** `src/game_cycle/database/schema.sql` (addition)

```sql
CREATE TABLE IF NOT EXISTS rivalries (
    rivalry_id TEXT PRIMARY KEY,
    dynasty_id TEXT NOT NULL,
    team_a_id INTEGER NOT NULL,
    team_b_id INTEGER NOT NULL,
    rivalry_type TEXT NOT NULL,  -- 'division', 'historic', 'geographic', 'recent'
    rivalry_name TEXT,
    intensity INTEGER DEFAULT 50,
    is_protected INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(dynasty_id, team_a_id, team_b_id),
    CHECK(team_a_id < team_b_id),  -- Enforce ordering
    CHECK(intensity BETWEEN 1 AND 100)
);

CREATE INDEX idx_rivalries_team ON rivalries(dynasty_id, team_a_id);
CREATE INDEX idx_rivalries_team_b ON rivalries(dynasty_id, team_b_id);
```

### 1.5 Acceptance Criteria ✅ COMPLETE (77 tests passing)

- [x] Rivalry model with type enum, intensity, protection flag
- [x] Static config with 20+ historic/geographic rivalries
- [x] RivalryAPI with CRUD operations and dynasty isolation
- [x] All division matchups auto-created as DIVISION rivalries
- [x] Initialization service loads rivalries on dynasty creation
- [x] Unit tests: rivalry creation, lookup, intensity bounds (77 tests)

**Test File:** `tests/game_cycle/database/test_rivalry_api.py`

---

## Tollgate 2: Head-to-Head History Tracking

**Goal:** Track all-time records between teams for rivalry context.

### 2.1 Head-to-Head Data Model

**File:** `src/game_cycle/models/head_to_head.py`

```python
@dataclass
class HeadToHeadRecord:
    """All-time record between two teams."""
    team_a_id: int
    team_b_id: int
    team_a_wins: int
    team_b_wins: int
    ties: int
    team_a_home_wins: int
    team_a_away_wins: int
    last_meeting_season: int
    last_meeting_winner: Optional[int]
    current_streak_team: Optional[int]  # Team on winning streak
    current_streak_count: int
    playoff_meetings: int
    playoff_team_a_wins: int
    playoff_team_b_wins: int
```

### 2.2 Head-to-Head API

**File:** `src/game_cycle/database/head_to_head_api.py`

```python
class HeadToHeadAPI:
    """Track all-time records between teams."""

    def get_record(dynasty_id: str, team_a: int, team_b: int) -> HeadToHeadRecord
    def update_after_game(dynasty_id: str, game_result: GameResult) -> None
    def get_team_all_records(dynasty_id: str, team_id: int) -> List[HeadToHeadRecord]
    def get_biggest_rivalries_by_games(dynasty_id: str, limit: int = 10) -> List[HeadToHeadRecord]
```

### 2.3 Database Schema

```sql
CREATE TABLE IF NOT EXISTS head_to_head (
    dynasty_id TEXT NOT NULL,
    team_a_id INTEGER NOT NULL,
    team_b_id INTEGER NOT NULL,
    team_a_wins INTEGER DEFAULT 0,
    team_b_wins INTEGER DEFAULT 0,
    ties INTEGER DEFAULT 0,
    team_a_home_wins INTEGER DEFAULT 0,
    team_a_away_wins INTEGER DEFAULT 0,
    last_meeting_season INTEGER,
    last_meeting_winner INTEGER,
    current_streak_team INTEGER,
    current_streak_count INTEGER DEFAULT 0,
    playoff_meetings INTEGER DEFAULT 0,
    playoff_team_a_wins INTEGER DEFAULT 0,
    playoff_team_b_wins INTEGER DEFAULT 0,
    PRIMARY KEY (dynasty_id, team_a_id, team_b_id),
    CHECK(team_a_id < team_b_id)
);
```

### 2.4 Integration with Game Results

**File:** `src/game_cycle/handlers/regular_season.py` (modification)

After game completion, call `HeadToHeadAPI.update_after_game()` to:
- Increment win/loss/tie counts
- Update streak information
- Track home/away splits
- Flag if playoff game

### 2.5 Acceptance Criteria ✅ COMPLETE (69 tests passing)

- [x] HeadToHeadRecord model with comprehensive stats
- [x] HeadToHeadAPI with auto-update after games
- [x] Streak tracking (Bears have won 3 straight vs Lions)
- [x] Playoff meeting separation
- [x] Integration hook in RegularSeasonHandler and PlayoffHandler
- [x] Unit tests: record updates, streak calculation (69 tests)

**Test File:** `tests/game_cycle/database/test_head_to_head_api.py`

---

## Tollgate 3: Bye Week Implementation

**Goal:** Add mandatory bye weeks to the schedule (weeks 5-14).

### 3.1 Bye Week Constraints

NFL bye week rules:
- Each team gets exactly 1 bye week
- Bye weeks occur between weeks 5-14 (originally 4-13, expanded)
- Maximum 6 teams on bye per week (originally 4, now 6 with 17 games)
- No team plays Thursday after a Monday game without bye
- Teams coming off international games get following week bye

### 3.2 Schedule Generator Modification

**File:** `src/game_cycle/services/nfl_schedule_generator.py` (modification)

```python
def _distribute_to_weeks_with_byes(self, matchups: List[Matchup]) -> Dict[int, List[Matchup]]:
    """
    Distribute matchups to weeks 1-18 with bye weeks.

    Modified algorithm:
    1. Assign bye weeks first (weeks 5-14, max 4 teams per bye week)
    2. Then distribute games ensuring teams don't play during bye
    3. Week 18 has all 16 games (no byes)
    """

def _assign_bye_weeks(self) -> Dict[int, int]:
    """
    Assign bye week for each team.

    Returns:
        Dict mapping team_id -> bye_week

    Constraints:
    - Bye weeks 5-14 (10 weeks, 32 teams = ~3.2 teams/week average)
    - No division has all 4 teams on same bye
    - Balance early vs late byes across conference
    """
```

### 3.3 Bye Week Tracking

**File:** `src/game_cycle/database/schedule_api.py` (addition)

```python
def get_team_bye_week(dynasty_id: str, season: int, team_id: int) -> int
def get_teams_on_bye(dynasty_id: str, season: int, week: int) -> List[int]
def save_bye_weeks(dynasty_id: str, season: int, bye_assignments: Dict[int, int]) -> None
```

### 3.4 Database Schema

```sql
CREATE TABLE IF NOT EXISTS bye_weeks (
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    bye_week INTEGER NOT NULL,
    PRIMARY KEY (dynasty_id, season, team_id),
    CHECK(bye_week BETWEEN 5 AND 14)
);
```

### 3.5 UI Integration

**File:** `game_cycle_ui/views/schedule_view.py` (if exists, or new)

- Show "BYE" in schedule for bye weeks
- Filter option: "Hide bye weeks"
- Bye week indicator in weekly schedule display

### 3.6 Acceptance Criteria ✅ COMPLETE (26 tests passing)

- [x] Each team assigned exactly 1 bye week (weeks 5-14)
- [x] No more than 4 teams on bye per week
- [x] Division constraint: not all 4 teams same bye week
- [x] Schedule generator respects bye assignments
- [x] Bye weeks persisted in database
- [x] Unit tests: bye distribution, constraint validation (26 tests)

**Test File:** `tests/game_cycle/services/test_bye_week_scheduling.py`

---

## Tollgate 4: Primetime Game Scheduling

**Goal:** Assign games to primetime slots (TNF, SNF, MNF).

### 4.1 Time Slot Model

**File:** `src/game_cycle/models/game_slot.py`

```python
class GameSlot(Enum):
    """NFL broadcast time slots."""
    THURSDAY_NIGHT = "TNF"          # 8:20pm ET
    SUNDAY_EARLY = "SUN_EARLY"      # 1:00pm ET
    SUNDAY_LATE = "SUN_LATE"        # 4:05pm/4:25pm ET
    SUNDAY_NIGHT = "SNF"            # 8:20pm ET
    MONDAY_NIGHT = "MNF"            # 8:15pm ET

    # Special slots
    THANKSGIVING_EARLY = "TG_EARLY"  # 12:30pm ET
    THANKSGIVING_LATE = "TG_LATE"    # 4:30pm ET
    THANKSGIVING_NIGHT = "TG_NIGHT"  # 8:20pm ET
    CHRISTMAS = "XMAS"
    INTERNATIONAL = "INTL"           # London/Germany/Mexico

@dataclass
class PrimetimeAssignment:
    """Primetime game assignment."""
    game_id: str
    slot: GameSlot
    broadcast_network: str  # NBC, ESPN, NFL Network, Amazon
    is_flex_eligible: bool  # Can be flexed in/out weeks 12-17
```

### 4.2 Primetime Assignment Algorithm

**File:** `src/game_cycle/services/primetime_scheduler.py`

```python
class PrimetimeScheduler:
    """
    Assign games to primetime slots based on matchup quality.

    Primetime priorities:
    1. Historic rivalries (Bears-Packers)
    2. Division games between contenders
    3. Super Bowl rematch
    4. Star QBs facing off
    5. Games with playoff implications (late season)
    """

    def assign_primetime_games(
        self,
        season: int,
        matchups: List[Matchup],
        rivalries: List[Rivalry],
        standings: Dict[int, Standing]  # Prior year standings for initial assignment
    ) -> Dict[str, PrimetimeAssignment]:
        """
        Assign primetime slots for the season.

        Distribution per week:
        - 1 Thursday Night (except Week 1: NFL Kickoff)
        - 1 Sunday Night
        - 1 Monday Night (some weeks have 2)
        - 3-4 Sunday Late games
        - Remaining: Sunday Early
        """

    def calculate_matchup_appeal(
        self,
        home_team: int,
        away_team: int,
        rivalry: Optional[Rivalry],
        prior_standings: Dict[int, Standing]
    ) -> int:
        """
        Score matchup for primetime consideration (0-100).

        Factors:
        - Rivalry intensity (+30 max)
        - Combined win total from prior year (+25 max)
        - Market size of teams (+20 max)
        - Star player factor (+15 max)
        - Division implications (+10 max)
        """
```

### 4.3 Special Game Designations

```python
def assign_special_games(self, season: int, matchups: List[Matchup]) -> None:
    """
    Assign special game designations.

    - Thanksgiving: 3 games (Lions home, Cowboys home, prime matchup)
    - Christmas (if on weekend): 2-3 games
    - Week 1 Kickoff: Defending champion hosts Thursday
    - International: 4-5 games (London, Germany, Mexico)
    """
```

### 4.4 Database Schema

```sql
CREATE TABLE IF NOT EXISTS game_slots (
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    game_id TEXT NOT NULL,
    slot TEXT NOT NULL,  -- 'TNF', 'SNF', 'MNF', etc.
    broadcast_network TEXT,
    is_flex_eligible INTEGER DEFAULT 1,
    flexed_from TEXT,  -- Original slot if flexed
    PRIMARY KEY (dynasty_id, game_id)
);
```

### 4.5 Acceptance Criteria ✅ COMPLETE (23 tests passing)

- [x] GameSlot enum with all NFL time slots
- [x] PrimetimeScheduler assigns games by appeal score
- [x] Each week has correct primetime distribution
- [x] Thanksgiving games: Lions, Cowboys, + 1 prime
- [x] Week 1: Defending champion hosts Thursday kickoff
- [x] Market size and rivalry boost primetime chances
- [x] Unit tests: slot assignment, appeal calculation (23 tests)

**Test File:** `tests/game_cycle/services/test_primetime_scheduler.py`

---

## Tollgate 5: Rivalry Gameplay Effects

**Goal:** Rivalries affect player performance and game simulation.

### 5.1 Rivalry Modifier System

**File:** `src/game_management/rivalry_modifiers.py`

```python
@dataclass
class RivalryGameModifiers:
    """Modifiers applied during rivalry games."""
    offensive_boost: float      # 0.95-1.08 multiplier
    defensive_boost: float
    turnover_variance: float    # Higher variance = more chaos
    penalty_rate_modifier: float  # Rivalry games = more penalties
    crowd_noise_boost: float    # Home field advantage amplified

def calculate_rivalry_modifiers(
    rivalry: Rivalry,
    head_to_head: HeadToHeadRecord,
    home_team_id: int,
    game_context: GameContext
) -> RivalryGameModifiers:
    """
    Calculate gameplay modifiers for a rivalry game.

    Intensity effects (scaled by rivalry.intensity):
    - High intensity (80+): More variance, more penalties, higher stakes
    - Medium (50-79): Moderate boost to both teams
    - Low (20-49): Slight atmosphere boost

    Streak effects:
    - Team on losing streak: Desperation boost (+3% offense)
    - Team on winning streak: Confidence boost (+2% defense)

    Revenge game:
    - Lost last meeting: +5% motivation
    - Blowout loss last meeting: +8% motivation
    """
```

### 5.2 Integration with Game Engine

**File:** `src/play_engine/core/engine.py` (modification)

```python
def _apply_game_modifiers(self, play_params: PlayParams) -> PlayParams:
    """Apply rivalry modifiers to play parameters."""
    if self._rivalry_modifiers:
        play_params.offensive_efficiency *= self._rivalry_modifiers.offensive_boost
        play_params.defensive_efficiency *= self._rivalry_modifiers.defensive_boost
        play_params.turnover_chance *= self._rivalry_modifiers.turnover_variance
```

### 5.3 Rivalry Event Generation

**File:** `src/game_management/random_events.py` (addition)

```python
def generate_rivalry_events(rivalry: Rivalry, quarter: int) -> List[GameEvent]:
    """
    Generate rivalry-specific random events.

    Possible events:
    - Chippy play after whistle (+15% personal foul chance)
    - Crowd influence (momentum swing after big play)
    - Player ejection (rare, high-intensity rivalries only)
    - Bench-clearing scuffle (very rare, cosmetic)
    """
```

### 5.4 Acceptance Criteria ✅ COMPLETE (40 tests passing)

- [x] RivalryGameModifiers applied during game simulation
- [x] Intensity scales modifier strength (LEGENDARY to MINIMAL)
- [x] Streak/revenge game bonuses calculated
- [x] Higher penalty rates in rivalry games (up to +35%)
- [x] Turnover variance increases with intensity (up to +40%)
- [x] Crowd noise boost for home field advantage (up to +25%)
- [x] Integration with GameLoopController (momentum_modifier, crowd_noise)
- [x] Unit tests: modifier calculation, head-to-head effects (40 tests)

**Test File:** `tests/game_management/test_rivalry_modifiers.py`

---

## Tollgate 6: Dynamic Rivalry Evolution

**Goal:** Rivalries intensify/diminish based on game outcomes.

### 6.1 Intensity Update Rules

**File:** `src/game_cycle/services/rivalry_service.py`

```python
class RivalryService:
    """Manage rivalry intensity evolution."""

    def update_rivalry_after_game(
        self,
        dynasty_id: str,
        rivalry: Rivalry,
        game_result: GameResult
    ) -> None:
        """
        Update rivalry intensity after a game.

        Intensity increases:
        - Close game (within 7 points): +3-5
        - Overtime game: +5-8
        - Playoff meeting: +10-15
        - Controversial ending: +5-10
        - Season sweep: -2 (one-sided = less rivalry)

        Intensity decreases:
        - Blowout (20+ points): -3-5
        - Non-competitive season: -5 per year
        - Division realignment: Reset to base
        """

    def create_new_rivalry(
        self,
        dynasty_id: str,
        team_a: int,
        team_b: int,
        trigger: str  # 'playoff_meeting', 'controversial_game', 'new_division'
    ) -> Optional[Rivalry]:
        """
        Create a new RECENT rivalry based on events.

        Triggers:
        - Teams meet in playoffs (intensity = 60)
        - 3+ close games in 2 years (intensity = 50)
        - Controversial finish (intensity = 55)
        """

    def decay_inactive_rivalries(self, dynasty_id: str, season: int) -> None:
        """
        Annual decay for rivalries without recent meetings.

        RECENT rivalries decay -10/year without meeting
        Below 20 intensity = rivalry removed
        HISTORIC rivalries never decay below 50
        """
```

### 6.2 Playoff Rivalry Boost

```python
def process_playoff_rivalry_impact(
    self,
    dynasty_id: str,
    playoff_matchup: PlayoffMatchup
) -> None:
    """
    Playoff meetings significantly boost rivalry intensity.

    - Wild Card: +10 intensity
    - Divisional: +12 intensity
    - Conference Championship: +15 intensity
    - Super Bowl: +20 intensity, create HISTORIC if none exists
    """
```

### 6.3 Acceptance Criteria ✅ COMPLETE (34 tests passing)

- [x] Close games increase rivalry intensity (+4 to +6)
- [x] Blowouts decrease intensity (-4)
- [x] Overtime games boost intensity (+7)
- [x] Playoff meetings create/boost rivalries (+10 to +20 based on round)
- [x] RECENT rivalries decay without meetings (-10/year)
- [x] HISTORIC rivalries protected from decay (never below 50)
- [x] DIVISION rivalries protected (never below 40)
- [x] New rivalries auto-created from playoff history (intensity 60-70)
- [x] Integration with regular_season.py handler
- [x] Integration with playoffs.py handler
- [x] Decay hook in offseason.py (_execute_honors)
- [x] Unit tests: intensity changes, decay logic (34 tests)

**Test File:** `tests/game_cycle/services/test_rivalry_service.py`

---

## Tollgate 7: Schedule UI & Rivalry Display

**Goal:** Display schedule with rivalry indicators and primetime games.

### 7.1 Schedule View Enhancement

**File:** `game_cycle_ui/views/schedule_view.py`

```python
class ScheduleView(QWidget):
    """
    Enhanced schedule view with rivalry and primetime indicators.

    Features:
    - Weekly schedule grid
    - Rivalry game highlighting (color-coded by intensity)
    - Primetime slot badges (TNF, SNF, MNF)
    - Bye week display
    - Click game for head-to-head history popup
    """
```

### 7.2 Rivalry Info Dialog

**File:** `game_cycle_ui/dialogs/rivalry_info_dialog.py`

```python
class RivalryInfoDialog(QDialog):
    """
    Display rivalry details and head-to-head history.

    Shows:
    - Rivalry name and type
    - All-time record
    - Current streak
    - Recent meetings (last 5 games)
    - Intensity meter visualization
    - Playoff history between teams
    """
```

### 7.3 Team Schedule Widget

```python
class TeamScheduleWidget(QWidget):
    """
    Single team's 17-game schedule.

    Columns:
    - Week
    - Opponent (with rivalry icon if applicable)
    - Home/Away
    - Time Slot (with network logo)
    - Result (after game played)
    - Rivalry indicator (flame icon for high intensity)
    """
```

### 7.4 Visual Indicators

```python
# Rivalry intensity colors
RIVALRY_COLORS = {
    (80, 100): "#FF4444",  # Red - Intense rivalry
    (60, 79): "#FF8800",   # Orange - Strong rivalry
    (40, 59): "#FFCC00",   # Yellow - Moderate rivalry
    (20, 39): "#88CC00",   # Light green - Mild rivalry
    (1, 19): "#CCCCCC",    # Gray - Minimal rivalry
}

# Primetime badges
SLOT_BADGES = {
    GameSlot.THURSDAY_NIGHT: ("TNF", "#00AA00"),
    GameSlot.SUNDAY_NIGHT: ("SNF", "#0066CC"),
    GameSlot.MONDAY_NIGHT: ("MNF", "#CC0000"),
}
```

### 7.5 Acceptance Criteria

- [x] Schedule view shows full 18-week schedule
- [x] Rivalry games visually highlighted by intensity
- [x] Primetime games show slot badges
- [x] Bye weeks clearly indicated
- [x] Click game opens rivalry info dialog
- [x] Head-to-head history displayed
- [x] Team filter to view single team's schedule
- [x] 36 UI tests passing

**Test File:** `tests/game_cycle_ui/views/test_schedule_view.py`

**Files Created:**
- `game_cycle_ui/views/schedule_view.py` (~480 lines)
- `game_cycle_ui/dialogs/rivalry_info_dialog.py` (~300 lines)
- `game_cycle_ui/widgets/team_schedule_widget.py` (~200 lines)
- Theme constants added to `game_cycle_ui/theme.py`
- ScheduleView registered in `game_cycle_ui/main_window.py`

---

## Tollgate 8: Flex Scheduling (Late Season)

**Goal:** Allow primetime game adjustments in final weeks.

### 8.1 Flex Scheduling Rules

NFL flex rules:
- Weeks 12-17: SNF games can be flexed
- Weeks 15-17: TNF, MNF can also be flexed
- 12-day notice required (we'll auto-flex)
- Games with playoff implications prioritized

### 8.2 Flex Scheduler

**File:** `src/game_cycle/services/flex_scheduler.py`

```python
class FlexScheduler:
    """
    Adjust primetime games based on playoff implications.

    Runs after each week during weeks 11-17 to evaluate
    flex opportunities for upcoming primetime slots.
    """

    def evaluate_flex_opportunities(
        self,
        dynasty_id: str,
        season: int,
        current_week: int
    ) -> List[FlexRecommendation]:
        """
        Identify games that should be flexed into/out of primetime.

        Criteria:
        - Playoff implications (clinch, elimination scenarios)
        - Division title implications
        - Current standings vs preseason expectations
        - Rivalry intensity
        """

    def execute_flex(
        self,
        dynasty_id: str,
        game_to_flex_in: str,
        game_to_flex_out: str,
        new_slot: GameSlot
    ) -> None:
        """Execute a flex schedule change."""
```

### 8.3 Playoff Implications Calculator

```python
def calculate_playoff_implications(
    standings: Dict[int, Standing],
    week: int,
    home_team: int,
    away_team: int
) -> PlayoffImplications:
    """
    Calculate what's at stake in this game.

    Returns:
    - can_clinch_playoff: bool
    - can_clinch_division: bool
    - can_clinch_bye: bool
    - elimination_game: bool
    - wild_card_implications: bool
    """
```

### 8.4 Acceptance Criteria ✅ COMPLETE (28 tests passing)

- [x] Flex evaluation runs weeks 10-15 (to flex weeks 12-17 with 12-day notice)
- [x] Games with playoff implications prioritized via PlayoffImplications
- [x] Flex changes recorded in database (execute_flex updates game_slots)
- [x] UI shows "★" indicator for flexed games with tooltip
- [x] Original slot preserved in flexed_from field
- [x] Unit tests: flex recommendation logic, appeal calculation (28 tests)

**Test File:** `tests/game_cycle/services/test_flex_scheduler.py`

**Files Created:**
- `src/game_cycle/services/flex_scheduler.py` (~750 lines) - FlexScheduler, PlayoffImplications, FlexRecommendation
- `tests/game_cycle/services/test_flex_scheduler.py` (~280 lines)

**Files Modified:**
- `src/game_cycle/handlers/regular_season.py` - Added `_evaluate_flex_scheduling()` hook
- `game_cycle_ui/views/schedule_view.py` - Added flex indicator (★) and legend
- `src/game_cycle/services/__init__.py` - Exported FlexScheduler, PlayoffImplications, FlexRecommendation

---

## Database Schema Summary

All new tables for Milestone 11:

```sql
-- Tollgate 1: Rivalries
CREATE TABLE rivalries (...);

-- Tollgate 2: Head-to-Head
CREATE TABLE head_to_head (...);

-- Tollgate 3: Bye Weeks
CREATE TABLE bye_weeks (...);

-- Tollgate 4: Game Slots
CREATE TABLE game_slots (...);
```

---

## Integration Points

### With Existing Systems

| System | Integration |
|--------|-------------|
| Game Engine (M9) | Rivalry modifiers applied during simulation |
| Statistics (M4) | Head-to-head records from game results |
| Player Personas (M7) | Rivalry games affect player motivation |
| Team Statistics (M8) | Rivalry record displayed in team stats |
| Injuries (M5) | Higher injury variance in rivalry games |

### Future Integrations

| Future Milestone | Integration |
|------------------|-------------|
| Media Coverage (#13) | Rivalry games get more coverage |
| Social Media (#14) | Fans react to rivalry outcomes |
| Player Popularity (#15) | Big rivalry performances boost popularity |
| Press Conferences (#16) | Questions about upcoming rivalry games |

---

## Test Summary

| Tollgate | Test File | Key Tests |
|----------|-----------|-----------|
| 1 | `test_rivalry_api.py` | Rivalry CRUD, division auto-creation |
| 2 | `test_head_to_head_api.py` | Record updates, streak tracking |
| 3 | `test_bye_week_scheduling.py` | Distribution, constraints |
| 4 | `test_primetime_scheduler.py` | Slot assignment, appeal scoring |
| 5 | `test_rivalry_modifiers.py` | Gameplay effects, variance |
| 6 | `test_rivalry_service.py` | Intensity evolution, decay |
| 7 | `test_schedule_view.py` | UI rendering, dialogs |
| 8 | `test_flex_scheduler.py` | Flex recommendations |

---

## Success Metrics

1. **272 games** correctly scheduled with bye weeks
2. **32 teams** each have exactly 1 bye week (weeks 5-14)
3. **~30 rivalry matchups** per season identified
4. **Primetime games** show higher average intensity scores
5. **Rivalry games** produce statistically different outcomes (more variance)
6. **Flex scheduling** moves 2-4 games per season into primetime

---

## Estimated Scope

| Tollgate | New Files | Modified Files | Complexity |
|----------|-----------|----------------|------------|
| 1 | 3 | 1 | Medium |
| 2 | 2 | 2 | Medium |
| 3 | 1 | 2 | High |
| 4 | 2 | 1 | High |
| 5 | 2 | 2 | Medium |
| 6 | 1 | 0 | Medium |
| 7 | 3 | 0 | Medium |
| 8 | 1 | 1 | Medium |

**Total:** ~15 new files, ~9 modifications