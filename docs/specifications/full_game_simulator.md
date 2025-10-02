# FullGameSimulator Class Specification

## Overview
**Class**: `FullGameSimulator`
**Location**: `src/game_management/full_game_simulator.py`
**Purpose**: Complete NFL game simulator with modular architecture for simulating full NFL games between two teams

## Description
A clean, modular NFL game simulator designed for incremental feature development. Orchestrates complete NFL games including coin toss, drive management, play-by-play simulation, statistics tracking, and game results.

---

## Constructor

### `__init__(away_team_id: int, home_team_id: int, overtime_type: str = "regular_season")`

**Parameters**:
- `away_team_id` (int): Numerical team ID for away team (1-32)
- `home_team_id` (int): Numerical team ID for home team (1-32)
- `overtime_type` (str): Type of overtime rules - `"regular_season"` or `"playoffs"` (default: `"regular_season"`)

**Raises**:
- `ValueError`: If away/home team cannot be loaded
- `ValueError`: If both teams have the same ID

**Initialization Actions**:
- Loads team data using numerical team IDs
- Validates team loading and ensures different teams
- Loads complete team rosters
- Loads coaching staff configurations for both teams
- Initializes GameManager for core game management
- Executes coin toss and determines possession
- Displays initialization summary with team details

---

## Core Methods

### Game Simulation

#### `simulate_game(date=None) -> GameResult`
**Purpose**: Execute complete NFL game simulation from kickoff to final whistle

**Parameters**:
- `date` (optional): Game date for record-keeping

**Returns**: `GameResult` object containing:
- Final score (team ID-keyed dictionary)
- Winner (Team object or None for tie)
- Total plays executed
- Total drives completed
- Game duration in minutes
- Drive-by-drive results
- Comprehensive player/team statistics

**Process**:
1. Initializes GameLoopController with all game components
2. Creates overtime manager based on configured overtime type
3. Runs complete game simulation
4. Tracks simulation performance metrics
5. Displays final results summary
6. Stores results internally for API access

**Error Handling**: Falls back to minimal game state if simulation fails

---

### Team Information Access

#### `get_team_info() -> Dict`
Returns detailed information about both teams including:
- Team ID, name, city, nickname, abbreviation
- Conference, division
- Team colors
- Roster size

#### `get_away_roster() -> List[Player]`
Returns complete away team roster as list of Player objects

#### `get_home_roster() -> List[Player]`
Returns complete home team roster as list of Player objects

#### `get_roster_by_team(team_id: int) -> List[Player]`
Returns roster for specified team ID

**Raises**: `ValueError` if team_id not in game

#### `get_starting_lineup(team_id: int, position_group: str = None) -> List[Player]`
Returns starting players, optionally filtered by position, sorted by overall rating (highest first)

#### `get_team_depth_chart(team_id: int) -> Dict[str, List[Player]]`
Returns organized depth chart with positions as keys and sorted player lists as values

---

### Coaching Staff Access

#### `get_away_coaching_staff() -> Dict`
Returns away team coaching staff configuration

#### `get_home_coaching_staff() -> Dict`
Returns home team coaching staff configuration

#### `get_coaching_staff_by_team(team_id: int) -> Dict`
Returns coaching staff for specified team ID

**Raises**: `ValueError` if team_id not in game

---

### Game State Access

#### `get_game_status() -> Dict`
Returns comprehensive current game state:
- Current quarter
- Time remaining (formatted display)
- Game phase (pregame, first_half, halftime, second_half, overtime, final)
- Current scores for both teams
- Team abbreviations
- Halftime status
- Two-minute warning status

#### `get_game_clock() -> GameClock`
Returns GameClock object for time tracking

#### `get_scoreboard() -> Scoreboard`
Returns Scoreboard object for scoring operations

#### `get_possession_manager() -> PossessionManager`
Returns PossessionManager for possession tracking

#### `get_field_tracker() -> FieldTracker`
Returns current drive's FieldTracker (or None if no active drive)

#### `get_current_field_position() -> Optional[int]`
Returns current ball field position (or None if no active drive)

#### `get_coin_toss_results() -> Dict`
Returns coin toss results:
- Winner team name
- Receiving team name
- Opening kickoff team name

---

### Results Access (Post-Simulation)

#### `get_game_result() -> Optional[GameResult]`
Returns complete GameResult object with all game data, or None if no game simulated

#### `get_final_score() -> Dict[str, Any]`
Returns enhanced final score with metadata:
- `scores`: Team ID-keyed scores (e.g., `{22: 21, 23: 14}`)
- `team_names`: Team ID to name mapping
- `winner_id`: Winning team ID or None
- `winner_name`: Winning team name or None
- `total_plays`: Total plays executed
- `total_drives`: Total drives completed
- `game_duration_minutes`: Game length in minutes
- `game_completed`: Boolean completion status
- `simulation_time`: Actual simulation runtime in seconds

---

## Private Helper Methods

#### `_load_coaching_staff(team_id: int) -> Dict`
Loads coaching staff configuration from JSON files:
- Reads team coaching styles mapping
- Loads head coach, offensive coordinator, defensive coordinator configs
- Falls back to generic staff if configs unavailable

#### `_get_fallback_coaching_staff(team_id: int) -> Dict`
Returns generic coaching staff when real configs unavailable

#### `_get_team_name(team_id: int) -> str`
Converts team ID to display name

#### `_create_fallback_game_result(game_state, start_time, date) -> GameResult`
Creates minimal GameResult when full simulation fails

---

## Magic Methods

#### `__str__() -> str`
Returns: `"FullGameSimulator(AWAY @ HOME)"` with team abbreviations

#### `__repr__() -> str`
Returns: `"FullGameSimulator(away_team_id=X, home_team_id=Y)"`

---

## Dependencies

**External Modules**:
- `team_management.teams.team_loader`: Team data loading
- `team_management.personnel`: Roster generation
- `constants.team_ids`: Team ID constants
- `game_management.game_manager`: Core game management
- `game_management.game_loop_controller`: Game loop orchestration
- `game_management.overtime_manager`: Overtime rules management

**Configuration Files**:
- `src/config/team_coaching_styles.json`: Team-to-coach mappings
- `src/config/coaching_staff/head_coaches/*.json`: Head coach configs
- `src/config/coaching_staff/offensive_coordinators/*.json`: OC configs
- `src/config/coaching_staff/defensive_coordinators/*.json`: DC configs

---

## Usage Example

```python
from game_management.full_game_simulator import FullGameSimulator
from constants.team_ids import TeamIDs

# Initialize game
simulator = FullGameSimulator(
    away_team_id=TeamIDs.DETROIT_LIONS,
    home_team_id=TeamIDs.GREEN_BAY_PACKERS,
    overtime_type="playoffs"
)

# Run simulation
result = simulator.simulate_game(date="2024-01-15")

# Access results
final_score = simulator.get_final_score()
print(f"Winner: {final_score['winner_name']}")
print(f"Final Score: {final_score['scores']}")
```

---

## Key Features

✅ **Modular Architecture**: Clean separation of concerns
✅ **Comprehensive Statistics**: Full player and team stat tracking
✅ **Realistic Coaching**: JSON-based coaching staff with real NFL coaches
✅ **Overtime Support**: Both regular season and playoff overtime rules
✅ **Error Handling**: Graceful fallbacks for missing configurations
✅ **Performance Tracking**: Simulation timing and metrics
✅ **Rich API**: Complete access to game state, rosters, and results