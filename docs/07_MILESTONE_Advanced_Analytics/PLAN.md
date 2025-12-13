# Milestone 7: Advanced Analytics & PFF Grades

## Overview

Implement a comprehensive player grading system inspired by Pro Football Focus (PFF), providing granular performance evaluation for every player on every play. The system calculates per-play grades (0-100 scale), aggregates them to game/season/career levels, and computes advanced metrics like EPA, Success Rate, and position-specific performance indicators.

**Status**: COMPLETE
**Dependencies**: Statistics (#4) - Complete
**Scope**: FULL simulation mode only, full granularity storage, standalone (no integrations), includes UI

### Completion Summary
All 6 tollgates implemented:
- Tollgate 1: Database schema (4 tables), models, and APIs
- Tollgate 2: GradingAlgorithm protocol with context-aware grading
- Tollgate 3: 7 position-specific graders (QB, RB, WR, OL, DL, LB, DB)
- Tollgate 4: EPA calculator, success rate, and advanced metrics
- Tollgate 5: AnalyticsService with play engine integration
- Tollgate 6: StatsAPI extensions and AnalyticsView UI

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Simulation Mode | FULL only | Grades require per-play data unavailable in INSTANT mode |
| Storage Granularity | Full (per-play + aggregates) | Enables detailed breakdown analysis and historical tracking |
| Integrations | Standalone | Build core system first; integrate with Trade/Awards/GM later |
| UI | Included | Add analytics view to game_cycle_ui for grade visualization |

---

## Tollgate Structure

### Tollgate 1: Foundation & Database Schema
- Add 4 new tables to schema.sql
- Create `src/analytics/` directory structure
- Create dataclass models
- Create database APIs (PlayGradesAPI, AnalyticsAPI)
- Unit tests for database operations

### Tollgate 2: Core Grading Algorithm
- Implement GradingAlgorithm protocol
- Implement StandardGradingAlgorithm with context-aware grading
- Grade aggregation functions (play → game → season)
- Unit tests for grading logic

### Tollgate 3: Position-Specific Graders
- Implement 7 position grader modules (QB, RB, WR, OL, DL, LB, DB)
- Position-specific component weights and calculation logic
- Unit tests for each grader

### Tollgate 4: Advanced Metrics Calculation
- EPA (Expected Points Added) calculator
- Success rate calculation
- Air yards, YAC, pressure metrics
- Unit tests for metric calculations

### Tollgate 5: Service Integration with Play Engine
- Create AnalyticsService orchestration layer
- Integrate with play engine (PlayResult → grades)
- Integrate with regular season handler for persistence
- Integration tests for end-to-end grading

### Tollgate 6: Query API & UI View
- Extend StatsAPI with grade query methods
- Create AnalyticsView for game_cycle_ui
- Grade leaderboards and player cards
- UI integration tests

---

## Database Schema

### New Tables

```sql
-- Per-play grades (FULL simulation mode)
CREATE TABLE player_play_grades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    game_id TEXT NOT NULL,
    play_number INTEGER NOT NULL,

    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    position TEXT NOT NULL,

    -- Context
    quarter INTEGER,
    down INTEGER,
    distance INTEGER,
    yard_line INTEGER,
    game_clock INTEGER,
    score_differential INTEGER,
    play_type TEXT,
    is_offense BOOLEAN,

    -- Grade
    play_grade REAL NOT NULL,
    grade_component_1 REAL,
    grade_component_2 REAL,
    grade_component_3 REAL,

    -- Outcome
    was_positive_play BOOLEAN,
    epa_contribution REAL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
);

CREATE INDEX idx_play_grades_game ON player_play_grades(dynasty_id, game_id);
CREATE INDEX idx_play_grades_player ON player_play_grades(dynasty_id, player_id);

-- Aggregated game grades
CREATE TABLE player_game_grades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    game_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,

    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    position TEXT NOT NULL,

    overall_grade REAL NOT NULL,

    -- Position-specific sub-grades
    passing_grade REAL,
    rushing_grade REAL,
    receiving_grade REAL,
    pass_blocking_grade REAL,
    run_blocking_grade REAL,
    pass_rush_grade REAL,
    run_defense_grade REAL,
    coverage_grade REAL,
    tackling_grade REAL,

    -- Snaps
    offensive_snaps INTEGER DEFAULT 0,
    defensive_snaps INTEGER DEFAULT 0,
    special_teams_snaps INTEGER DEFAULT 0,

    -- Metrics
    epa_total REAL,
    success_rate REAL,
    play_count INTEGER DEFAULT 0,
    positive_plays INTEGER DEFAULT 0,
    negative_plays INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(dynasty_id, game_id, player_id)
);

CREATE INDEX idx_game_grades_season ON player_game_grades(dynasty_id, season);
CREATE INDEX idx_game_grades_player ON player_game_grades(dynasty_id, player_id);

-- Season-aggregated grades
CREATE TABLE player_season_grades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,

    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    position TEXT NOT NULL,

    overall_grade REAL NOT NULL,

    -- Position-specific grades
    passing_grade REAL,
    rushing_grade REAL,
    receiving_grade REAL,
    pass_blocking_grade REAL,
    run_blocking_grade REAL,
    pass_rush_grade REAL,
    run_defense_grade REAL,
    coverage_grade REAL,
    tackling_grade REAL,

    -- Totals
    total_snaps INTEGER DEFAULT 0,
    games_graded INTEGER DEFAULT 0,
    total_plays_graded INTEGER DEFAULT 0,
    positive_play_rate REAL,

    -- EPA
    epa_total REAL,
    epa_per_play REAL,

    -- Rankings
    position_rank INTEGER,
    overall_rank INTEGER,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(dynasty_id, season, player_id)
);

-- Advanced metrics per game
CREATE TABLE advanced_game_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    game_id TEXT NOT NULL,
    team_id INTEGER NOT NULL,

    -- EPA
    epa_total REAL,
    epa_passing REAL,
    epa_rushing REAL,
    epa_per_play REAL,

    -- Success Rates
    success_rate REAL,
    passing_success_rate REAL,
    rushing_success_rate REAL,

    -- Passing advanced
    air_yards_total INTEGER,
    yac_total INTEGER,
    completion_pct_over_expected REAL,
    avg_time_to_throw REAL,
    pressure_rate REAL,

    -- Defensive advanced
    pass_rush_win_rate REAL,
    coverage_success_rate REAL,
    missed_tackle_rate REAL,
    forced_incompletions INTEGER,
    qb_hits INTEGER,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(dynasty_id, game_id, team_id)
);
```

---

## Architecture

### Directory Structure

```
src/analytics/
├── __init__.py
├── models.py                    # Dataclasses: PlayGrade, GameGrade, SeasonGrade, AdvancedMetrics
├── grading_constants.py         # Position weights, thresholds, EPA lookup tables
├── grading_algorithm.py         # GradingAlgorithm protocol + StandardGradingAlgorithm
├── advanced_metrics.py          # EPACalculator, SuccessRateCalculator
├── position_graders/
│   ├── __init__.py
│   ├── base_grader.py           # Abstract base class with common logic
│   ├── qb_grader.py             # Accuracy, decision, pocket presence, deep ball
│   ├── rb_grader.py             # Vision, elusiveness, pass blocking, receiving
│   ├── wr_grader.py             # Route running, separation, contested catches, blocking
│   ├── ol_grader.py             # Pass blocking, run blocking, penalties
│   ├── dl_grader.py             # Pass rush, run defense, versatility
│   ├── lb_grader.py             # Coverage, tackling, blitzing, run fits
│   └── db_grader.py             # Man coverage, zone coverage, ball skills, tackling
└── services/
    └── analytics_service.py     # Orchestrates grading, aggregation, storage

src/game_cycle/database/
├── play_grades_api.py           # CRUD for player_play_grades table
└── analytics_api.py             # CRUD for game/season grades + advanced metrics

game_cycle_ui/views/
└── analytics_view.py            # UI view for grades and metrics
```

### Key Dataclasses

```python
# src/analytics/models.py

@dataclass
class PlayContext:
    """Context for grading a single play."""
    game_id: str
    play_number: int
    quarter: int
    down: int
    distance: int
    yard_line: int
    game_clock: int
    score_differential: int
    play_type: str
    is_offense: bool

@dataclass
class PlayGrade:
    """Per-play grade for a single player."""
    player_id: int
    game_id: str
    play_number: int
    position: str
    play_grade: float  # 0-100
    grade_components: Dict[str, float]
    was_positive_play: bool
    epa_contribution: float
    context: PlayContext

@dataclass
class GameGrade:
    """Game-aggregated grade for a player."""
    player_id: int
    game_id: str
    season: int
    week: int
    position: str
    team_id: int
    overall_grade: float

    # Position-specific sub-grades (Optional)
    passing_grade: Optional[float] = None
    rushing_grade: Optional[float] = None
    receiving_grade: Optional[float] = None
    pass_blocking_grade: Optional[float] = None
    run_blocking_grade: Optional[float] = None
    pass_rush_grade: Optional[float] = None
    run_defense_grade: Optional[float] = None
    coverage_grade: Optional[float] = None
    tackling_grade: Optional[float] = None

    # Metrics
    epa_total: float = 0.0
    success_rate: float = 0.0
    play_count: int = 0
    positive_plays: int = 0
    negative_plays: int = 0

@dataclass
class SeasonGrade:
    """Season-aggregated grade with rankings."""
    player_id: int
    season: int
    position: str
    team_id: int
    overall_grade: float
    position_rank: int
    overall_rank: int
    games_graded: int
    total_plays_graded: int
    epa_total: float
    epa_per_play: float

@dataclass
class AdvancedMetrics:
    """Advanced metrics for a game/team."""
    game_id: str
    team_id: int
    epa_total: float
    epa_passing: float
    epa_rushing: float
    epa_per_play: float
    success_rate: float
    passing_success_rate: float
    rushing_success_rate: float
    air_yards_total: int
    yac_total: int
    completion_pct_over_expected: float
    pressure_rate: float
```

---

## Grading Algorithm

### Grade Scale
| Grade Range | Description | Frequency |
|-------------|-------------|-----------|
| 90-100 | Elite | Top 5% of plays |
| 80-89 | Above Average | Positive contribution |
| 60-79 | Neutral | Expected performance |
| 40-59 | Below Average | Negative contribution |
| 0-39 | Poor | Significant negative impact |

### Core Algorithm Flow

```
1. Receive PlayStatsSummary from play engine
2. For each player on the field:
   a. Get position-specific grader
   b. Calculate component grades (accuracy, blocking, coverage, etc.)
   c. Apply context modifiers (clutch, red zone, critical down)
   d. Calculate weighted overall grade
   e. Determine positive/negative play
   f. Calculate EPA contribution
3. Store per-play grades
4. After game: aggregate to game grade
5. After season: aggregate to season grade with rankings
```

### Context Modifiers

| Situation | Modifier | Rationale |
|-----------|----------|-----------|
| 4th quarter, close game (±8 pts) | 1.10x | Clutch performance matters more |
| Red zone (≤20 yard line) | 1.05x | High-leverage situation |
| 3rd/4th down | 1.05x | Critical downs |
| Garbage time (4th Q, ±21 pts) | 0.90x | Lower-stakes situation |

### Position-Specific Components

**QB**: accuracy (30%), decision (25%), pocket_presence (20%), deep_ball (15%), mobility (10%)

**RB**: vision (25%), elusiveness (25%), power (20%), pass_blocking (15%), receiving (15%)

**WR/TE**: route_running (25%), separation (25%), contested_catches (20%), blocking (15%), yac (15%)

**OL**: pass_blocking (45%), run_blocking (45%), penalties (10%)

**DL**: pass_rush (40%), run_defense (40%), versatility (20%)

**LB**: coverage (30%), tackling (30%), blitzing (20%), run_fits (20%)

**DB**: coverage (40%), ball_skills (25%), tackling (20%), zone_awareness (15%)

---

## Advanced Metrics

### EPA (Expected Points Added)

EPA measures the value a play adds compared to expected points before the play.

```python
EPA_FIELD_POSITION = {
    # Own territory (negative EP)
    1: -1.5, 10: -0.8, 20: -0.3, 30: 0.1, 40: 0.5, 50: 1.0,
    # Opponent territory (positive EP)
    60: 1.6, 70: 2.5, 80: 3.5, 90: 5.0, 99: 6.5
}

def calculate_epa(start_yard, end_yard, start_down, end_down, is_turnover, is_score, points):
    start_ep = expected_points(start_yard, start_down)
    if is_score:
        return points - start_ep
    if is_turnover:
        opponent_ep = expected_points(100 - end_yard, 1)
        return -start_ep - opponent_ep
    end_ep = expected_points(end_yard, end_down)
    return end_ep - start_ep
```

### Success Rate

A play is "successful" if it gains:
- 1st down: ≥40% of yards to go
- 2nd down: ≥50% of yards to go
- 3rd/4th down: 100% of yards to go (conversion)

```python
def is_successful_play(down, distance, yards_gained):
    thresholds = {1: 0.40, 2: 0.50, 3: 1.0, 4: 1.0}
    return yards_gained >= distance * thresholds[down]
```

---

## Service Layer

### AnalyticsService

```python
class AnalyticsService:
    """Orchestrates grading and metrics calculation."""

    def __init__(self, dynasty_id: str, conn: sqlite3.Connection):
        self.dynasty_id = dynasty_id
        self.conn = conn
        self.grading_algorithm = StandardGradingAlgorithm()
        self.epa_calculator = EPACalculator()
        self.play_grades_api = PlayGradesAPI(conn)
        self.analytics_api = AnalyticsAPI(conn)

    def grade_game(self, game_result: GameResult, play_by_play: List[PlayResult]) -> List[GameGrade]:
        """Grade all players in a game from play-by-play data."""
        all_play_grades: Dict[int, List[PlayGrade]] = defaultdict(list)

        for play_num, play in enumerate(play_by_play):
            context = self._build_context(game_result.game_id, play_num, play)

            for player_stats in play.player_stats_summary.player_stats:
                grade = self.grading_algorithm.grade_play(context, player_stats, play)
                all_play_grades[player_stats.player_id].append(grade)
                self.play_grades_api.insert_play_grade(self.dynasty_id, grade)

        # Aggregate to game grades
        game_grades = []
        for player_id, grades in all_play_grades.items():
            game_grade = self.grading_algorithm.aggregate_to_game(grades)
            game_grades.append(game_grade)
            self.analytics_api.insert_game_grade(self.dynasty_id, game_grade)

        return game_grades

    def update_season_grades(self, season: int) -> List[SeasonGrade]:
        """Recalculate season grades and rankings for all players."""
        game_grades = self.analytics_api.get_all_game_grades(self.dynasty_id, season)

        # Group by player
        by_player = defaultdict(list)
        for gg in game_grades:
            by_player[gg.player_id].append(gg)

        season_grades = []
        for player_id, grades in by_player.items():
            sg = self.grading_algorithm.aggregate_to_season(grades)
            season_grades.append(sg)

        # Calculate rankings
        self._calculate_rankings(season_grades)

        # Persist
        for sg in season_grades:
            self.analytics_api.upsert_season_grade(self.dynasty_id, sg)

        return season_grades
```

---

## UI View

### AnalyticsView Components

1. **Grade Leaderboard**: Top players by overall grade with position filter
2. **Player Grade Card**: Individual player with grade history graph
3. **Team Grades**: All players on a team sorted by position/grade
4. **Game Breakdown**: Per-play grades for a specific game
5. **Advanced Metrics Table**: EPA, success rate, pressure rate by team

### Integration with game_cycle_ui

```python
# game_cycle_ui/views/analytics_view.py

class AnalyticsView(StageView):
    """View for displaying player grades and advanced analytics."""

    def __init__(self, stage_controller: StageController):
        super().__init__(stage_controller)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Tab widget for different views
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_leaderboard_tab(), "Leaderboard")
        self.tabs.addTab(self._create_team_grades_tab(), "Team Grades")
        self.tabs.addTab(self._create_advanced_metrics_tab(), "Advanced Metrics")

        layout.addWidget(self.tabs)

    def _create_leaderboard_tab(self) -> QWidget:
        """Grade leaderboard with position filter."""
        # Position dropdown, grade table, player detail on click
        ...

    def _create_team_grades_tab(self) -> QWidget:
        """All players on selected team with grades."""
        # Team selector, sortable table by position/grade
        ...

    def _create_advanced_metrics_tab(self) -> QWidget:
        """Team-level advanced metrics comparison."""
        # EPA, success rate, pressure rate by team
        ...
```

---

## StatsAPI Extensions

```python
# Add to src/statistics/stats_api.py

def get_player_season_grade(self, player_id: str, season: int) -> Optional[SeasonGrade]:
    """Get season grade for a specific player."""

def get_grade_leaders(
    self,
    season: int,
    position: Optional[str] = None,
    limit: int = 25
) -> List[SeasonGrade]:
    """Get top players by overall grade."""

def get_player_grade_history(
    self,
    player_id: str,
    num_games: int = 10
) -> List[GameGrade]:
    """Get recent game grades for a player."""

def get_team_grades(self, team_id: int, season: int) -> List[SeasonGrade]:
    """Get all player grades for a team."""

def get_game_grades(self, game_id: str) -> List[GameGrade]:
    """Get all player grades from a specific game."""

def get_advanced_metrics(self, season: int) -> List[AdvancedMetrics]:
    """Get advanced metrics for all teams in a season."""
```

---

## Integration Points (Future)

These integrations are deferred to future milestones:

| System | Integration | Future Milestone |
|--------|-------------|------------------|
| Awards (#9) | Grades influence All-Pro/MVP voting | Awards milestone |
| Trade Value (#5) | Add grade factor to player value | Trade System (#6) |
| GM Behaviors (#35) | Grade trends inform FA/trade targets | GM AI milestone |
| Player Progression (#1) | Grades indicate development trajectory | Enhancement |
| Scouting (#23) | Prospect grades inform draft decisions | Scouting milestone |

---

## Testing Strategy

### Unit Tests
- Grade calculation edge cases (0 snaps, extreme values)
- Position-specific grader accuracy
- EPA calculation correctness
- Database API CRUD operations
- Grade aggregation math

### Integration Tests
- End-to-end game simulation with grading
- Grade aggregation from play → game → season
- Dynasty isolation verification
- UI data binding

### Validation Tests
- Grade distribution is realistic (bell curve around 60)
- High-rated players average higher grades
- EPA sums approximate actual scoring
- Season leaders are plausible

---

## Critical Files

### Files to Modify
| File | Changes |
|------|---------|
| `src/game_cycle/database/schema.sql` | Add 4 new tables |
| `src/game_cycle/database/full_schema.sql` | Add 4 new tables |
| `src/statistics/stats_api.py` | Add grade query methods |
| `src/game_cycle/handlers/regular_season.py` | Call AnalyticsService after game |
| `game_cycle_ui/main_window.py` | Add analytics view to navigation |
| `game_cycle_ui/views/__init__.py` | Export AnalyticsView |

### New Files to Create
| File | Purpose |
|------|---------|
| `src/analytics/__init__.py` | Package init |
| `src/analytics/models.py` | Dataclasses |
| `src/analytics/grading_constants.py` | Weights, thresholds |
| `src/analytics/grading_algorithm.py` | Core grading logic |
| `src/analytics/advanced_metrics.py` | EPA, success rate |
| `src/analytics/position_graders/*.py` | 8 files (base + 7 positions) |
| `src/analytics/services/analytics_service.py` | Orchestration |
| `src/game_cycle/database/play_grades_api.py` | Play grades CRUD |
| `src/game_cycle/database/analytics_api.py` | Aggregated grades CRUD |
| `game_cycle_ui/views/analytics_view.py` | UI view |
| `tests/analytics/test_*.py` | Test files |

---

## Estimated Scope

- **New Code**: ~3,500 lines across 15+ files
- **Test Code**: ~1,500 lines
- **Tollgates**: 6
- **Tables**: 4 new