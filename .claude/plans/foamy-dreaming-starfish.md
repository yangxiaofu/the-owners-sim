# Fix Box Score Team Stats (First Downs, 3rd/4th Down, TOP, Penalties)

## Root Cause

The box score dialog shows these stats as zero because:

1. `regular_season.py:192-193` calls `BoxScoresAPI.aggregate_from_player_stats()` to build box scores
2. This method can only compute stats available from player stats (yards, turnovers)
3. It explicitly sets team-level stats to zero (see `box_scores_api.py:524-531`)

**However**, the game simulation DOES track these stats:
- `TeamGameStats` class tracks first_downs, 3rd/4th down, TOP, penalties
- `GameLoopController` returns these in `game_result.home_team_stats` / `away_team_stats`
- But this data is never passed to `box_scores_insert()`

---

## Fix Strategy

**Option 1 (Selected)**: Include team stats in `GameSimulationResult` and use them when saving box scores.

### Changes Required

#### 1. Update `GameSimulationResult` dataclass
**File:** `src/game_cycle/services/game_simulator_service.py`

Add team stats fields:
```python
@dataclass
class GameSimulationResult:
    ...
    home_team_stats: Dict[str, Any] = field(default_factory=dict)  # Add
    away_team_stats: Dict[str, Any] = field(default_factory=dict)  # Add
```

#### 2. Update `_simulate_full()` to extract team stats
**File:** `src/game_cycle/services/game_simulator_service.py`

In `_simulate_full()`, pass team stats to the result:
```python
return GameSimulationResult(
    ...
    home_team_stats=game_result.home_team_stats or {},  # Add
    away_team_stats=game_result.away_team_stats or {},  # Add
)
```

#### 3. Update `regular_season.py` to use team stats
**File:** `src/game_cycle/handlers/regular_season.py`

Replace the `aggregate_from_player_stats` call with proper team stats:
```python
# Build box scores from team stats (not just player stats)
home_box = sim_result.home_team_stats.copy() if sim_result.home_team_stats else {}
away_box = sim_result.away_team_stats.copy() if sim_result.away_team_stats else {}

# Ensure required fields exist (fill from player stats as fallback)
if not home_box.get('total_yards'):
    fallback = BoxScoresAPI.aggregate_from_player_stats(sim_result.player_stats, home_team_id)
    home_box.update({k: v for k, v in fallback.items() if k not in home_box or not home_box[k]})
```

#### 4. Update `playoffs.py` similarly
**File:** `src/game_cycle/handlers/playoffs.py`

Same changes as regular_season.py.

#### 5. Handle INSTANT mode (mock stats)
**File:** `src/game_cycle/services/mock_stats_generator.py`

Generate realistic mock team stats in INSTANT mode:
```python
def _generate_team_stats(self, team_id, home_score, away_score, total_yards):
    return {
        'first_downs': int(total_yards / 15),  # ~15 yds per first down
        'third_down_att': random.randint(10, 18),
        'third_down_conv': random.randint(3, 9),
        'fourth_down_att': random.randint(0, 3),
        'fourth_down_conv': random.randint(0, 2),
        'penalties': random.randint(3, 10),
        'penalty_yards': random.randint(20, 80),
        'time_of_possession': random.randint(1500, 2100),  # 25-35 min in seconds
        ...
    }
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/game_cycle/services/game_simulator_service.py` | Add team_stats fields to dataclass, populate in _simulate_full |
| `src/game_cycle/handlers/regular_season.py` | Use team_stats instead of aggregate_from_player_stats |
| `src/game_cycle/handlers/playoffs.py` | Same as regular_season.py |
| `src/game_cycle/services/mock_stats_generator.py` | Generate mock team-level stats for INSTANT mode |

---

## Field Mapping

| TeamGameStats Field | BoxScore Field |
|---------------------|----------------|
| first_downs | first_downs |
| third_down_attempts | third_down_att |
| third_down_conversions | third_down_conv |
| fourth_down_attempts | fourth_down_att |
| fourth_down_conversions | fourth_down_conv |
| time_of_possession_seconds | time_of_possession |
| penalties | penalties |
| penalty_yards | penalty_yards |