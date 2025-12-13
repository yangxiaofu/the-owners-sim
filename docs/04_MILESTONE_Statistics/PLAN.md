# Milestone 4: Statistics & Record Keeping

## Goal

Integrate game statistics into main2.py (game cycle) using a phased approach: mock stats generator first (fast mode), then real play-by-play engine integration later. Track player and team stats across the season for league leaders, box scores, and historical records.

**User Choices:**
- Stat Weighting: Rating-Weighted (elite players get better stats)
- Stat Scope: Full Stats (all 40+ columns)
- UI Timing: Backend First (stats generation/persistence before UI)

---

## Progress Summary

| Tollgate | Status | Description |
|----------|--------|-------------|
| 1 | **COMPLETE** | MockStatsGenerator Core |
| 2 | **COMPLETE** | Stats Database Integration |
| 3 | **COMPLETE** | Unit & Integration Tests |
| 4 | **COMPLETE** | Stats UI - StatsView |
| 5 | **COMPLETE** | Stats UI - BoxScoreDialog |
| 6 | **COMPLETE** | MainWindow Integration (done with T4) |
| 7 | **COMPLETE** | Real Engine Integration (Hybrid Mode) |

**Current Phase:** Milestone 4 COMPLETE - All 7 Tollgates Done

---

## Tollgates

### Tollgate 1: MockStatsGenerator Core - COMPLETE

**Goal**: Create a mock stats generator that produces realistic player stats matching the final score.

**Files Created:**
- `src/game_cycle/services/mock_stats_generator.py` (~800 lines)

**Tasks:**
- [x] Create `MockStatsGenerator` class in `src/game_cycle/services/mock_stats_generator.py`
- [x] Implement score decomposition algorithm (TDs, FGs, XPs from score)
- [x] Implement passing stats allocation (rating-weighted to QBs)
- [x] Implement rushing stats allocation (to RBs, QBs)
- [x] Implement receiving stats allocation (must equal passing yards)
- [x] Implement defensive stats allocation (tackles distributed across defense)
- [x] Implement special teams stats (kicker FGs/XPs)
- [x] Create `MockGameStats` dataclass for output

**Key Features Implemented:**
- Rating-weighted stat allocation (elite players get better stats)
- Score decomposition: `score // 7 = TDs`, `(score % 7) // 3 = FGs`
- Passing/receiving consistency: `passing_yards == sum(receiving_yards)`
- Full 40+ stat columns supported
- Passer rating calculation
- Fantasy points calculation

**Acceptance Criteria:**
- [x] Generated passing yards == sum of receiving yards (consistency)
- [x] Score roughly matches TDs*6 + FGs*3 + XPs (within 3 points)
- [x] Higher-rated players get better stats on average
- [x] All position groups get appropriate stats

---

### Tollgate 2: Stats Database Integration - COMPLETE

**Goal**: Add stats persistence methods to UnifiedDatabaseAPI and integrate with RegularSeasonHandler.

**Files Modified:**
- `src/database/unified_api.py` - Added 4 stats methods
- `src/game_cycle/handlers/regular_season.py` - Integrated MockStatsGenerator

**Tasks:**
- [x] Add `stats_insert_game_stats()` method to UnifiedDatabaseAPI
- [x] Add `stats_get_game_stats()` method
- [x] Add `stats_get_season_leaders()` method
- [x] Add `stats_get_player_season_totals()` method
- [x] Modify `RegularSeasonHandler.execute()` to call MockStatsGenerator
- [x] Persist stats after each game simulation
- [x] Ensure dynasty_id isolation in all queries

**API Methods Added:**
```python
def stats_insert_game_stats(
    self, game_id: str, season: int, week: int,
    season_type: str, player_stats: List[Dict]
) -> int:
    """Batch insert player game stats. Returns row count."""

def stats_get_game_stats(self, game_id: str) -> List[Dict]:
    """Get all player stats for a specific game."""

def stats_get_season_leaders(
    self, season: int, stat: str, limit: int = 25
) -> List[Dict]:
    """Get league leaders for a stat (passing_yards, rushing_tds, etc.)."""

def stats_get_player_season_totals(
    self, player_id: str, season: int
) -> Dict:
    """Get aggregated season stats for a player."""
```

**Integration Note:** Game result must be inserted BEFORE stats due to FK constraint:
```python
# In RegularSeasonHandler.execute():
# 1. Insert game result FIRST (FK requirement)
unified_api.games_insert_result({...})

# 2. Generate and persist stats AFTER game exists
mock_stats = stats_generator.generate(...)
unified_api.stats_insert_game_stats(...)
```

**Acceptance Criteria:**
- [x] Stats persisted to database after each game
- [x] `stats_get_game_stats()` returns correct data
- [x] `stats_get_season_leaders()` returns sorted results
- [x] Dynasty isolation maintained (no cross-dynasty data)

---

### Tollgate 3: Unit & Integration Tests - COMPLETE

**Goal**: Comprehensive test coverage for mock stats generation and persistence.

**Files Created:**
- `tests/game_cycle/services/test_mock_stats_generator.py` (11 tests)
- `tests/game_cycle/services/test_stats_persistence.py` (9 tests)

**Unit Tests (11 passing):**
- `test_initialization` - MockStatsGenerator can be instantiated
- `test_generate_returns_mock_stats` - Returns MockGameStats object
- `test_score_decomposition` - TDs/FGs/XPs estimated correctly
- `test_passing_yards_equal_receiving_yards` - Consistency check
- `test_rating_weighted_values` - Elite players get better stats
- `test_all_stat_columns_present` - All 40+ columns populated
- `test_positions_covered` - All position groups have stats
- `test_passer_rating_calculation` - NFL passer rating formula
- `test_fantasy_points_calculation` - PPR fantasy scoring
- `test_high_scoring_game` - Handles 50+ point games
- `test_low_scoring_game` - Handles low-scoring defensive battles

**Integration Tests (9 passing):**
- `test_generate_and_persist_single_game` - Full insert flow
- `test_stats_survive_reload` - Persistence across connections
- `test_season_leaders_aggregation` - Leaders aggregate correctly
- `test_player_season_totals` - Season totals work
- `test_dynasty_isolation` - No cross-dynasty data leakage
- `test_multiple_games_same_week` - Multiple games handled
- `test_high_scoring_game_persistence` - High scores persist
- `test_defensive_shutout_persistence` - Shutouts work
- `test_all_stat_columns_persisted` - All columns saved

**Acceptance Criteria:**
- [x] 11 unit tests for MockStatsGenerator
- [x] 9 integration tests for persistence
- [x] All 20 tests passing

---

### Tollgate 4: Stats UI - StatsView - COMPLETE

**Goal**: Create a Stats tab in the main window showing league leaders and team stats.

**Files Created/Modified:**
- `game_cycle_ui/views/stats_view.py` (~450 lines) - NEW
- `game_cycle_ui/main_window.py` - MODIFIED (added Stats tab)
- `src/database/unified_api.py` - MODIFIED (added summary methods)

**Features Implemented:**
- 5 category tabs: Passing, Rushing, Receiving, Defense, Kicking
- Summary panel showing Games Played, Players, Current Week
- Season selector dropdown (last 5 years)
- Refresh button with auto-refresh after week simulation
- Team abbreviations via TeamDataLoader
- Position abbreviations mapping
- NFL passer rating calculation
- Leader highlighting (top player in green)

**Layout**:
```
+------------------------------------------------------------------+
| STATS                                        [Season: 2025 v]     |
+------------------------------------------------------------------+
| Summary: 256 Games | 4,128 Players | Week 12                      |
+------------------------------------------------------------------+
| [Passing] [Rushing] [Receiving] [Defense] [Kicking]               |
+------------------------------------------------------------------+
| # | Player         | Pos | Team | CMP | ATT | YDS | TD | INT | RTG|
|---|----------------|-----|------|-----|-----|-----|----|----|-----|
| 1 | P. Mahomes     | QB  | KC   | 402 | 612 | 4856| 38 | 10 |108.2|
| 2 | J. Allen       | QB  | BUF  | 378 | 589 | 4234| 32 | 12 | 98.4|
+------------------------------------------------------------------+
```

**API Methods Added:**
- `stats_get_game_count(season)` - Count of games with stats
- `stats_get_player_count(season)` - Count of players with stats
- `stats_get_current_week(season)` - Max week with stats

**Acceptance Criteria:**
- [x] StatsView widget created with 5 category tabs
- [x] League leaders populate from database via UnifiedDatabaseAPI
- [x] Tab switching shows different stat tables
- [x] Stats tab visible in main window
- [x] Stats auto-refresh after simulating weeks
- [x] Team abbreviations display correctly
- [x] Passer rating calculated correctly

---

### Tollgate 5: Stats UI - BoxScoreDialog - COMPLETE
**Goal**: Create a box score dialog that shows full game stats.

**Files Created/Modified:**
- `game_cycle_ui/dialogs/box_score_dialog.py` (~320 lines) - NEW
- `game_cycle_ui/dialogs/__init__.py` - MODIFIED (export BoxScoreDialog)
- `game_cycle_ui/views/stage_view.py` - MODIFIED (added double-click handler, context storage)
- `game_cycle_ui/main_window.py` - MODIFIED (pass context to StageView)

**Features Implemented:**
- Double-click on played game in StageView opens BoxScoreDialog
- 4 stat sections per team: Passing, Rushing, Receiving, Defense
- Players filtered by actual stats (only show players with relevant stats)
- Sorted by primary stat (yards for offense, tackles for defense)
- Gracefully ignores double-clicks on unplayed games
- Scroll area for long stat lists
- Close button

**Layout**:
```
+------------------------------------------------------------------+
| BOX SCORE: KC 31 @ BUF 24                                         |
+==================================================================+
| [Scroll Area]                                                      |
|   KANSAS CITY CHIEFS (Home) - 31 pts                               |
|   PASSING: Player | CMP/ATT | YDS | TD | INT | RTG               |
|   RUSHING: Player | ATT | YDS | AVG | TD | LNG                   |
|   RECEIVING: Player | REC | TGT | YDS | AVG | TD                 |
|   DEFENSE: Player | TKL | SACK | INT | PD | FF                   |
|                                                                    |
|   BUFFALO BILLS (Away) - 24 pts                                    |
|   ... (same format)                                                |
+------------------------------------------------------------------+
|                                              [Close]              |
+------------------------------------------------------------------+
```

**Acceptance Criteria**:
- [x] BoxScoreDialog shows all stat sections
- [x] Dialog accessible from StageView game list via double-click
- [x] Stats formatted correctly (RTG calculated, AVG computed)
- [x] Unplayed games don't trigger dialog

---

### Tollgate 6: MainWindow Integration - COMPLETE

**Goal**: Integrate StatsView into the main window and wire up refreshes.

**Files Modified:**
- `game_cycle_ui/main_window.py` - Added Stats tab, wired refresh

**Implementation Note:**
A dedicated `StatsController` was not created. StatsView manages its own queries
via `set_context()` and `refresh_stats()` methods, which is sufficient for the
current scope. The main window triggers refresh via `stage_changed` signal.

**Tasks:**
- [x] Add "Stats" tab to main tab widget (line 117-119)
- [x] Wire refresh signal (line 122)
- [x] Refresh stats after each week simulated (lines 218-220)
- [x] Box score accessible from game schedule (Tollgate 5)
- [~] StatsController - Not needed, StatsView is self-contained

**Acceptance Criteria:**
- [x] Stats tab visible in main window
- [x] Stats refresh after advancing weeks
- [x] Box score accessible from game schedule

---

### Tollgate 7: Real Engine Integration (Hybrid Mode) - COMPLETE

**Goal**: Add simulation mode toggle allowing users to choose between fast mock stats (INSTANT) and real play-by-play simulation (FULL).

**Files Created/Modified:**
- `src/game_cycle/services/game_simulator_service.py` (~490 lines) - NEW
- `src/game_cycle/handlers/regular_season.py` - MODIFIED (use GameSimulatorService)
- `src/game_cycle/stage_controller.py` - MODIFIED (store/pass simulation mode)
- `game_cycle_ui/controllers/stage_controller.py` - MODIFIED (delegate mode setting)
- `game_cycle_ui/main_window.py` - MODIFIED (add toolbar toggle)

**Tasks:**
- [x] Create `GameSimulatorService` wrapper around `FullGameSimulator`
- [x] Add `SimulationMode` enum (INSTANT vs FULL)
- [x] Create `GameSimulationResult` dataclass for unified output
- [x] Implement `_simulate_instant()` using MockStatsGenerator
- [x] Implement `_simulate_full()` using FullGameSimulator
- [x] Convert FullGameSimulator's ~20 fields to database's 50+ fields
- [x] Add passer rating and fantasy points calculation
- [x] Wire mode through backend StageController
- [x] Add UI toggle in MainWindow toolbar (QComboBox)
- [x] Show info message when switching to Full Sim mode

**Architecture:**
```
UI Toolbar Toggle (QComboBox)
       ↓
StageUIController.set_simulation_mode(mode)
       ↓
Backend StageController._simulation_mode
       ↓
Context dict: {"simulation_mode": "instant" | "full"}
       ↓
RegularSeasonHandler.execute(context)
       ↓
GameSimulatorService.simulate_game(mode=...)
       ↓
if mode == FULL:
    FullGameSimulator → _convert_player_stats() → 50+ field dict
else:
    MockStatsGenerator → player_stats list
       ↓
UnifiedDatabaseAPI.stats_insert_game_stats()
```

**Key Classes:**
```python
class SimulationMode(Enum):
    INSTANT = "instant"  # Fast mock stats (~1s/week)
    FULL = "full"        # Real play-by-play (~3-5s/game)

@dataclass
class GameSimulationResult:
    game_id: str
    home_team_id: int
    away_team_id: int
    home_score: int
    away_score: int
    total_plays: int = 0
    game_duration_minutes: int = 0
    overtime_periods: int = 0
    player_stats: List[Dict[str, Any]] = field(default_factory=list)
```

**Performance:**
| Mode | Time for 16 games | Play-by-Play Data |
|------|-------------------|-------------------|
| Instant | ~1-2 seconds | No |
| Full | ~45-80 seconds | Yes |

**Acceptance Criteria:**
- [x] UI toggle visible in toolbar (Instant/Full Sim dropdown)
- [x] Instant mode works exactly as before (no regression)
- [x] Full mode uses FullGameSimulator for play-by-play
- [x] Both modes produce stats compatible with Stats tab
- [x] Warning shown when switching to Full Sim mode
- [x] Game duration and total plays tracked in Full mode
- [x] No crashes when switching modes mid-season

---

## Files Created/Modified

| File | Action | Status |
|------|--------|--------|
| `src/game_cycle/services/mock_stats_generator.py` | CREATE | **DONE** |
| `src/game_cycle/services/game_simulator_service.py` | CREATE | **DONE** |
| `src/game_cycle/handlers/regular_season.py` | MODIFY | **DONE** |
| `src/game_cycle/stage_controller.py` | MODIFY | **DONE** |
| `src/database/unified_api.py` | MODIFY | **DONE** |
| `tests/game_cycle/services/test_mock_stats_generator.py` | CREATE | **DONE** |
| `tests/game_cycle/services/test_stats_persistence.py` | CREATE | **DONE** |
| `docs/04_MILESTONE_Statistics/PLAN.md` | CREATE | **DONE** |
| `game_cycle_ui/views/stats_view.py` | CREATE | **DONE** |
| `game_cycle_ui/main_window.py` | MODIFY | **DONE** |
| `game_cycle_ui/controllers/stage_controller.py` | MODIFY | **DONE** |
| `game_cycle_ui/dialogs/box_score_dialog.py` | CREATE | **DONE** |
| `game_cycle_ui/views/stage_view.py` | MODIFY | **DONE** |
| `game_cycle_ui/dialogs/__init__.py` | MODIFY | **DONE** |

---

## Acceptance Criteria (Milestone Complete)

- [x] Simulating a week generates player stats for all games
- [x] Stats persisted to `player_game_stats` table
- [x] Stats tab shows league leaders (passing, rushing, receiving, defense, kicking)
- [ ] Team stats viewable for any team (deferred to future)
- [x] Box score dialog shows full game stats (Tollgate 5)
- [x] Double-clicking a game in schedule shows box score (Tollgate 5)
- [x] Stats survive dynasty reload
- [x] 20+ tests passing (currently 20/20)

---

## Stat Categories Reference

### Passing Stats
- `passing_yards`, `passing_tds`, `passing_attempts`, `passing_completions`, `passing_interceptions`
- Calculated: `completion_pct`, `yards_per_attempt`, `passer_rating`

### Rushing Stats
- `rushing_yards`, `rushing_tds`, `rushing_attempts`
- Calculated: `yards_per_carry`

### Receiving Stats
- `receiving_yards`, `receiving_tds`, `receptions`, `targets`
- Calculated: `catch_rate`, `yards_per_reception`

### Defensive Stats
- `tackles_total`, `sacks`, `interceptions`, `passes_defended`, `forced_fumbles`, `tackles_for_loss`

### Special Teams Stats
- `field_goals_made`, `field_goals_attempted`, `extra_points_made`, `extra_points_attempted`
- Calculated: `field_goal_pct`

---

## Testing Strategy

### Unit Tests (11 passing)
- MockStatsGenerator: consistency, score matching, rating weighting
- All position groups covered

### Integration Tests (9 passing)
- Full week simulation with stats
- Season leaders aggregation
- Stats persistence across sessions
- Dynasty isolation

### Manual Testing (Pending for UI)
- Run full 17-week season
- Verify league leaders are realistic
- Verify box scores match final scores

---

**Certainty Score: 100/100** (All Tollgates Complete)
