# Milestone 8: Team Statistics

## Overview

Implement comprehensive team-level statistics tracking for offensive, defensive, and special teams performance. Aggregate player stats into team totals, calculate league-wide rankings (1-32), and provide a UI view for team statistics.

**Dependencies**: Statistics (#4 - Complete), Game Engine (Complete)
**Feeds Into**: Awards (#10), GM Behaviors (#36), Business Layer

---

## Goals

From DEVELOPMENT_PRIORITIES.md:
- **Offensive Stats**: Total yards, passing/rushing yards, first downs, 3rd/4th down efficiency
- **Defensive Stats**: Points allowed, yards allowed, sacks, TFLs, INTs, passes defended, defensive TDs
- **Special Teams**: Field goal %, extra point %, punt/kick return yards and TDs
- **Turnovers**: INTs thrown/caught, fumbles lost/recovered, turnover margin
- **Team Rankings (1-32)** for offensive, defensive, special teams categories

**Deferred** (requires full sim mode):
- Time of Possession
- Red Zone stats
- Quarter-by-Quarter scoring

---

## Current State

**What Exists:**
1. `player_game_stats` table - 60+ fields per player per game
2. `box_scores` table - schema exists (first downs, 3rd/4th down, yards, turnovers, ToP)
3. `standings` table - W/L, points for/against per team
4. `TeamStats`/`TeamStatsAccumulator` classes in `src/play_engine/simulation/stats.py`
5. `CentralizedStatsAggregator.get_team_statistics()` returns TeamStats object
6. `StatsView` UI - shows player league leaders only

**Gaps:**
1. No `TeamSeasonStatsAPI` following service layer pattern
2. Box scores table not populated during game simulation
3. No season-level team stat aggregation
4. No league-wide rankings (1-32)
5. No Team Stats UI tab

---

## Tollgate Plan

### Tollgate 1: TeamSeasonStatsAPI - Database Layer

**Goal**: Create a dedicated API class for team season statistics.

**Files to Create:**
- `src/game_cycle/database/team_stats_api.py` (~350 lines)
- `tests/game_cycle/database/test_team_stats_api.py`

**Deliverables:**
1. `TeamSeasonStats` dataclass with all stat categories
2. `TeamSeasonStatsAPI` class with:
   - `get_team_season_stats(dynasty_id, team_id, season)` - single team
   - `get_all_teams_season_stats(dynasty_id, season)` - all 32 teams
   - `get_team_game_stats(dynasty_id, team_id, game_id)` - per-game
   - `calculate_rankings(dynasty_id, season, stat_category)` - 1-32 rankings

**Data Model:**
```python
@dataclass
class TeamSeasonStats:
    team_id: int
    season: int
    games_played: int

    # Offensive
    total_yards: int
    passing_yards: int
    rushing_yards: int
    first_downs: int
    third_down_attempts: int
    third_down_conversions: int
    points_scored: int

    # Defensive (opponent's offense)
    points_allowed: int
    yards_allowed: int
    passing_yards_allowed: int
    rushing_yards_allowed: int
    sacks: float
    interceptions: int
    passes_defended: int
    forced_fumbles: int
    fumbles_recovered: int
    defensive_tds: int

    # Special Teams
    field_goals_made: int
    field_goals_attempted: int
    extra_points_made: int
    extra_points_attempted: int
    punt_return_yards: int
    punt_return_tds: int
    kick_return_yards: int
    kick_return_tds: int

    # Turnovers
    interceptions_thrown: int
    fumbles_lost: int
    turnovers: int
    turnovers_forced: int
    turnover_margin: int

    @property
    def yards_per_game(self) -> float:
        return self.total_yards / self.games_played if self.games_played else 0.0

    @property
    def points_per_game(self) -> float:
        return self.points_scored / self.games_played if self.games_played else 0.0

    @property
    def third_down_pct(self) -> float:
        return (self.third_down_conversions / self.third_down_attempts * 100) if self.third_down_attempts else 0.0

    @property
    def field_goal_pct(self) -> float:
        return (self.field_goals_made / self.field_goals_attempted * 100) if self.field_goals_attempted else 0.0
```

**Aggregation SQL Pattern:**
```sql
-- Offensive stats: aggregate team's own player stats
SELECT
    pgs.team_id,
    COUNT(DISTINCT pgs.game_id) as games_played,
    SUM(pgs.passing_yards) as passing_yards,
    SUM(pgs.rushing_yards) as rushing_yards,
    SUM(pgs.passing_yards + pgs.rushing_yards) as total_yards,
    SUM(pgs.passing_tds + pgs.rushing_tds + pgs.receiving_tds) as touchdowns,
    SUM(pgs.field_goals_made) as field_goals_made,
    SUM(pgs.interceptions_thrown) as interceptions_thrown,
    SUM(pgs.fumbles_lost) as fumbles_lost
FROM player_game_stats pgs
JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
WHERE pgs.dynasty_id = ? AND g.season = ?
GROUP BY pgs.team_id

-- Defensive stats: aggregate opponent's offense against this team
SELECT
    ? as team_id,
    SUM(pgs.passing_yards) as passing_yards_allowed,
    SUM(pgs.rushing_yards) as rushing_yards_allowed
FROM player_game_stats pgs
JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
WHERE pgs.dynasty_id = ? AND g.season = ?
  AND pgs.team_id != ?  -- opponent's players only
  AND (g.home_team_id = ? OR g.away_team_id = ?)  -- games involving target team
```

**Tests (5):**
- [ ] `test_get_team_season_stats_returns_correct_totals`
- [ ] `test_get_all_teams_returns_32_teams`
- [ ] `test_dynasty_isolation_prevents_cross_dynasty_data`
- [ ] `test_rankings_return_1_to_32`
- [ ] `test_empty_season_returns_zero_stats`

---

### Tollgate 2: Box Score Integration

**Goal**: Populate box_scores table during game simulation.

**Files to Create:**
- `src/game_cycle/database/box_scores_api.py` (~150 lines)
- `tests/game_cycle/database/test_box_scores_api.py`

**Files to Modify:**
- `src/game_cycle/handlers/regular_season.py` - persist box scores after game
- `src/game_cycle/handlers/playoffs.py` - persist box scores after game
- `src/database/unified_api.py` - add `box_scores_insert()` method

**Deliverables:**
1. `BoxScoresAPI` class with insert/retrieve methods
2. Box score persistence after each regular season game
3. Box score persistence after each playoff game
4. Calculate box score fields from player stat aggregations

**Box Score Fields (from schema):**
```python
@dataclass
class BoxScore:
    game_id: int
    team_id: int
    dynasty_id: str

    # Scoring by quarter (0 for mock mode)
    q1_score: int = 0
    q2_score: int = 0
    q3_score: int = 0
    q4_score: int = 0
    ot_score: int = 0

    # Efficiency
    first_downs: int = 0
    third_down_att: int = 0
    third_down_conv: int = 0
    fourth_down_att: int = 0
    fourth_down_conv: int = 0

    # Yardage
    total_yards: int = 0
    passing_yards: int = 0
    rushing_yards: int = 0

    # Turnovers & penalties
    turnovers: int = 0
    penalties: int = 0
    penalty_yards: int = 0

    # Time (0 for mock mode)
    time_of_possession: int = 0
```

**Integration Pattern (in regular_season.py):**
```python
# After game simulation, aggregate player stats to box score
def _create_box_score_from_player_stats(
    player_stats: List[Dict],
    team_id: int,
    final_score: int
) -> BoxScore:
    team_stats = [s for s in player_stats if s['team_id'] == team_id]
    return BoxScore(
        game_id=game_id,
        team_id=team_id,
        dynasty_id=dynasty_id,
        q4_score=final_score,  # All in Q4 for mock mode
        total_yards=sum(s.get('passing_yards', 0) + s.get('rushing_yards', 0) for s in team_stats),
        passing_yards=sum(s.get('passing_yards', 0) for s in team_stats),
        rushing_yards=sum(s.get('rushing_yards', 0) for s in team_stats),
        turnovers=sum(s.get('interceptions_thrown', 0) + s.get('fumbles_lost', 0) for s in team_stats),
    )
```

**Tests (4):**
- [ ] `test_insert_and_retrieve_box_score`
- [ ] `test_box_score_persisted_after_regular_season_game`
- [ ] `test_box_score_persisted_after_playoff_game`
- [ ] `test_box_score_totals_match_player_stats`

---

### Tollgate 3: Team Statistics Service Layer

**Goal**: Create service combining stats from multiple sources (follows service layer pattern).

**Files to Create:**
- `src/game_cycle/services/team_stats_service.py` (~250 lines)
- `tests/game_cycle/services/test_team_stats_service.py`

**Deliverables:**
1. `TeamStatsService` class (uses API classes, no direct SQL)
2. Methods:
   - `get_team_overview(team_id, season)` - combined view with rankings
   - `get_league_rankings(season)` - all stat categories
   - `get_team_comparison(team1_id, team2_id, season)` - head-to-head

**Service Pattern:**
```python
class TeamStatsService:
    """
    Service for team statistics operations.

    Follows service layer pattern - does NOT make direct database calls.
    Uses dedicated API classes for all data access.
    """

    def __init__(self, db_path: str, dynasty_id: str):
        self._dynasty_id = dynasty_id
        self._team_stats_api = TeamSeasonStatsAPI(db_path)
        self._standings_api = StandingsAPI(db_path)

    def get_team_overview(self, team_id: int, season: int) -> Dict[str, Any]:
        """Get comprehensive team stats including standings and rankings."""
        stats = self._team_stats_api.get_team_season_stats(
            self._dynasty_id, team_id, season
        )
        rankings = self._calculate_team_rankings(team_id, season)
        standing = self._standings_api.get_team_standing(
            self._dynasty_id, season, team_id
        )

        return {
            "team_id": team_id,
            "season": season,
            "stats": asdict(stats),
            "rankings": rankings,
            "standing": asdict(standing),
            "per_game": {
                "yards_per_game": stats.yards_per_game,
                "points_per_game": stats.points_per_game,
            }
        }

    def get_league_rankings(self, season: int) -> Dict[str, List]:
        """Get 1-32 rankings for all major stat categories."""
        return {
            "offensive": {
                "total_yards": self._team_stats_api.calculate_rankings(
                    self._dynasty_id, season, "total_yards"
                ),
                "points_scored": self._team_stats_api.calculate_rankings(
                    self._dynasty_id, season, "points_scored"
                ),
                "passing_yards": self._team_stats_api.calculate_rankings(
                    self._dynasty_id, season, "passing_yards"
                ),
                "rushing_yards": self._team_stats_api.calculate_rankings(
                    self._dynasty_id, season, "rushing_yards"
                ),
            },
            "defensive": {
                "points_allowed": self._team_stats_api.calculate_rankings(
                    self._dynasty_id, season, "points_allowed", ascending=True
                ),
                "yards_allowed": self._team_stats_api.calculate_rankings(
                    self._dynasty_id, season, "yards_allowed", ascending=True
                ),
                "sacks": self._team_stats_api.calculate_rankings(
                    self._dynasty_id, season, "sacks"
                ),
                "interceptions": self._team_stats_api.calculate_rankings(
                    self._dynasty_id, season, "interceptions"
                ),
            },
            "special_teams": {
                "field_goal_pct": self._team_stats_api.calculate_rankings(
                    self._dynasty_id, season, "field_goal_pct"
                ),
            },
            "turnovers": {
                "turnover_margin": self._team_stats_api.calculate_rankings(
                    self._dynasty_id, season, "turnover_margin"
                ),
            }
        }
```

**Tests (4):**
- [ ] `test_get_team_overview_combines_sources`
- [ ] `test_league_rankings_returns_all_categories`
- [ ] `test_team_comparison_returns_valid_data`
- [ ] `test_service_uses_api_classes_not_direct_sql`

---

### Tollgate 4: UnifiedDatabaseAPI Integration

**Goal**: Expose team stats through UnifiedDatabaseAPI for UI access.

**Files to Modify:**
- `src/database/unified_api.py` (~100 lines added)

**Methods to Add:**
```python
# Team Stats Methods (add to UnifiedDatabaseAPI class)

def team_stats_get_season(
    self, team_id: int, season: int, season_type: str = 'regular_season'
) -> Dict[str, Any]:
    """
    Get team season statistics.

    Args:
        team_id: Team ID (1-32)
        season: Season year
        season_type: 'regular_season' or 'playoffs'

    Returns:
        Dict with offensive, defensive, special teams stats
    """

def team_stats_get_all_teams(
    self, season: int, season_type: str = 'regular_season'
) -> List[Dict[str, Any]]:
    """
    Get stats for all 32 teams.

    Returns:
        List of team stat dicts, sorted by total yards descending
    """

def team_stats_get_rankings(
    self, season: int, category: str = 'total_yards',
    season_type: str = 'regular_season'
) -> List[Dict[str, Any]]:
    """
    Get team rankings 1-32 for a stat category.

    Args:
        category: One of 'total_yards', 'passing_yards', 'rushing_yards',
                  'points_scored', 'points_allowed', 'yards_allowed',
                  'sacks', 'interceptions', 'turnover_margin', 'field_goal_pct'

    Returns:
        List of {rank, team_id, team_name, value} ordered 1-32
    """

def team_stats_get_comparison(
    self, team1_id: int, team2_id: int, season: int
) -> Dict[str, Any]:
    """
    Compare two teams statistically.

    Returns:
        Dict with both teams' stats side-by-side
    """
```

**Tests (3):**
- [ ] `test_team_stats_get_rankings_orders_correctly`
- [ ] `test_team_stats_category_parameter`
- [ ] `test_team_stats_dynasty_isolation`

---

### Tollgate 5: Team Statistics UI View

**Goal**: Add "Team Stats" tab to StatsView showing team-level statistics with rankings.

**Files to Modify:**
- `game_cycle_ui/views/stats_view.py` (~150 lines added)

**Deliverables:**
1. "Team Stats" tab added to `category_tabs` (after existing tabs)
2. Team stats table with columns: Rank, Team, GP, Total YDS, Pass YDS, Rush YDS, PTS/G
3. View dropdown to switch between Offense/Defense/Special Teams
4. Wire refresh to update after simulating weeks

**UI Layout - Offense View:**
```
+------------------------------------------------------------------+
| LEAGUE STATS                              [Team: All v] [2025 v] |
+------------------------------------------------------------------+
| [Passing] [Rushing] [Receiving] [Defense] [Kicking] [TEAM STATS] |
+------------------------------------------------------------------+
| View: [Offense v]                                                 |
+------------------------------------------------------------------+
| # | Team          | GP | Total YDS | Pass YDS | Rush YDS | PTS/G |
|---|---------------|----|-----------+----------+----------+-------|
| 1 | Kansas City   | 12 |   4,856   |  3,245   |  1,611   | 28.4  |
| 2 | Buffalo       | 12 |   4,692   |  3,102   |  1,590   | 27.1  |
| 3 | Detroit       | 12 |   4,581   |  2,986   |  1,595   | 26.8  |
|...|    ...        | .. |    ...    |   ...    |   ...    |  ...  |
|32 | Carolina      | 12 |   3,102   |  1,956   |  1,146   | 14.2  |
+------------------------------------------------------------------+
```

**UI Layout - Defense View:**
```
+------------------------------------------------------------------+
| View: [Defense v]                                                 |
+------------------------------------------------------------------+
| # | Team          | GP | PTS Allow | YDS Allow | Sacks | INT | +/-|
|---|---------------|----|-----------+-----------+-------+-----+----|
| 1 | San Francisco | 12 |    186    |   3,012   |  38.0 |  14 | +12|
| 2 | Cleveland     | 12 |    192    |   3,145   |  42.5 |  12 | +10|
+------------------------------------------------------------------+
```

**Implementation Pattern:**
```python
def _create_category_tabs(self, parent_layout: QVBoxLayout):
    """Create tab widget with stat category tables."""
    self.category_tabs = QTabWidget()

    # ... existing tabs (Passing, Rushing, etc.)

    # Team Stats tab
    team_stats_widget = QWidget()
    team_stats_layout = QVBoxLayout(team_stats_widget)

    # View selector dropdown
    view_layout = QHBoxLayout()
    view_label = QLabel("View:")
    self.team_view_combo = QComboBox()
    self.team_view_combo.addItems(["Offense", "Defense", "Special Teams"])
    self.team_view_combo.currentIndexChanged.connect(self._on_team_view_changed)
    view_layout.addWidget(view_label)
    view_layout.addWidget(self.team_view_combo)
    view_layout.addStretch()
    team_stats_layout.addLayout(view_layout)

    # Team stats table
    self.team_stats_table = self._create_stats_table([
        "#", "Team", "GP", "Total YDS", "Pass YDS", "Rush YDS", "PTS/G"
    ])
    team_stats_layout.addWidget(self.team_stats_table)

    self.category_tabs.addTab(team_stats_widget, "Team Stats")
```

**Acceptance Criteria:**
- [ ] Team Stats tab visible in StatsView
- [ ] Teams ranked 1-32 by selected category
- [ ] Offense/Defense/Special Teams toggle works
- [ ] Data refreshes after simulating weeks
- [ ] Consistent styling with existing tabs

---

## Files Summary

| File | Action | Tollgate |
|------|--------|----------|
| `src/game_cycle/database/team_stats_api.py` | CREATE | 1 |
| `src/game_cycle/database/box_scores_api.py` | CREATE | 2 |
| `src/game_cycle/services/team_stats_service.py` | CREATE | 3 |
| `src/game_cycle/handlers/regular_season.py` | MODIFY | 2 |
| `src/game_cycle/handlers/playoffs.py` | MODIFY | 2 |
| `src/database/unified_api.py` | MODIFY | 2, 4 |
| `game_cycle_ui/views/stats_view.py` | MODIFY | 5 |
| `tests/game_cycle/database/test_team_stats_api.py` | CREATE | 1 |
| `tests/game_cycle/database/test_box_scores_api.py` | CREATE | 2 |
| `tests/game_cycle/services/test_team_stats_service.py` | CREATE | 3 |

---

## Critical Files to Reference

1. **`src/game_cycle/database/standings_api.py`** - API pattern to follow
2. **`src/database/unified_api.py`** - Add methods (~line 3383+ for stats methods)
3. **`src/game_cycle/handlers/regular_season.py`** - Box score insertion point
4. **`game_cycle_ui/views/stats_view.py`** - Add Team Stats tab (~line 188+)
5. **`src/game_cycle/database/schema.sql`** - box_scores and player_game_stats columns

---

## Testing Strategy

### Unit Tests (~16 tests total)
- **TeamSeasonStatsAPI**: 5 tests
- **BoxScoresAPI**: 4 tests
- **TeamStatsService**: 4 tests
- **UnifiedDatabaseAPI integration**: 3 tests

### Integration Tests
- Full season simulation produces correct team stats
- Rankings update after each game week
- Box scores match player stat aggregations

### Manual Testing Checklist
- [ ] Run full season, verify team rankings update weekly
- [ ] Compare top offensive team stats to actual player totals
- [ ] Verify turnover margin calculation (+/- logic)
- [ ] Verify defensive stats show opponent's offensive output
- [ ] Test Team Stats tab UI in all three views

---

## Certainty Score: 90/100

**High Confidence (95%):**
- API pattern is well-established (StandingsAPI, ProgressionHistoryAPI examples)
- Player stats aggregation queries are straightforward SQL GROUP BY
- UI pattern for category tabs exists in StatsView

**Medium Confidence (85%):**
- Defensive stats calculation requires careful join logic for opponent identification
- Box score population timing (ensure stats available before insertion)

**Lower Confidence (75%):**
- Time of possession, red zone, quarter scoring (deferred to future)