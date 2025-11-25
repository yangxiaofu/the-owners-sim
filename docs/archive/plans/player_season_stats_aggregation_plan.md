# Player Season Stats Aggregation Plan

## Problem Statement

**Current State:**
- `player_game_stats` table contains individual game records
- Season statistics require expensive `SUM()` + `GROUP BY` queries on every request
- Duplicate `player_id` values for same player cause players to appear multiple times in leaderboards
- No pre-computed metrics (passer rating, yards per carry, etc.)
- Performance degrades as more games are played

**Issues Identified:**
1. **Performance**: Leaderboard queries aggregate 1000+ rows every request
2. **Duplicates**: Same player appears multiple times due to duplicate player_ids and GROUP BY team_id
3. **Complexity**: UI code must filter and deduplicate results
4. **Missing Features**: Cannot efficiently query career stats or historical comparisons

## Proposed Solution

Create `player_season_stats` table following industry-standard sports database pattern (ESPN, Pro Football Reference):

**Two-tier architecture:**
- **Granular**: `player_game_stats` (game-by-game records for game logs)
- **Aggregated**: `player_season_stats` (season totals for leaderboards)

## Schema Design

### New Table: player_season_stats

```sql
CREATE TABLE player_season_stats (
    stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    player_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    team_id INTEGER NOT NULL,        -- Most recent team
    position TEXT NOT NULL,
    season INTEGER NOT NULL,

    -- Game counts
    games_played INTEGER DEFAULT 0,
    games_started INTEGER DEFAULT 0,

    -- Passing (raw stats)
    passing_attempts INTEGER DEFAULT 0,
    passing_completions INTEGER DEFAULT 0,
    passing_yards INTEGER DEFAULT 0,
    passing_tds INTEGER DEFAULT 0,
    passing_interceptions INTEGER DEFAULT 0,
    sacks_taken INTEGER DEFAULT 0,

    -- Passing (computed stats)
    completion_percentage REAL DEFAULT 0.0,
    yards_per_attempt REAL DEFAULT 0.0,
    passer_rating REAL DEFAULT 0.0,

    -- Rushing (raw stats)
    rushing_attempts INTEGER DEFAULT 0,
    rushing_yards INTEGER DEFAULT 0,
    rushing_tds INTEGER DEFAULT 0,
    rushing_long INTEGER DEFAULT 0,
    rushing_fumbles INTEGER DEFAULT 0,

    -- Rushing (computed stats)
    yards_per_carry REAL DEFAULT 0.0,
    yards_per_game_rushing REAL DEFAULT 0.0,

    -- Receiving (raw stats)
    targets INTEGER DEFAULT 0,
    receptions INTEGER DEFAULT 0,
    receiving_yards INTEGER DEFAULT 0,
    receiving_tds INTEGER DEFAULT 0,
    receiving_long INTEGER DEFAULT 0,
    receiving_fumbles INTEGER DEFAULT 0,

    -- Receiving (computed stats)
    catch_rate REAL DEFAULT 0.0,
    yards_per_reception REAL DEFAULT 0.0,
    yards_per_target REAL DEFAULT 0.0,
    yards_per_game_receiving REAL DEFAULT 0.0,

    -- Defense (raw stats)
    tackles_total INTEGER DEFAULT 0,
    tackles_solo INTEGER DEFAULT 0,
    tackles_assists INTEGER DEFAULT 0,
    sacks REAL DEFAULT 0.0,
    interceptions INTEGER DEFAULT 0,
    passes_defended INTEGER DEFAULT 0,
    forced_fumbles INTEGER DEFAULT 0,
    fumbles_recovered INTEGER DEFAULT 0,
    defensive_tds INTEGER DEFAULT 0,

    -- Special teams (raw stats)
    field_goals_made INTEGER DEFAULT 0,
    field_goals_attempted INTEGER DEFAULT 0,
    field_goal_long INTEGER DEFAULT 0,
    extra_points_made INTEGER DEFAULT 0,
    extra_points_attempted INTEGER DEFAULT 0,

    -- Special teams (computed stats)
    field_goal_percentage REAL DEFAULT 0.0,
    extra_point_percentage REAL DEFAULT 0.0,

    -- Metadata
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(dynasty_id, player_id, season)
);

-- Performance indexes
CREATE INDEX idx_season_stats_dynasty_season
    ON player_season_stats(dynasty_id, season);

CREATE INDEX idx_season_stats_passing_leaders
    ON player_season_stats(dynasty_id, season, passing_yards DESC);

CREATE INDEX idx_season_stats_rushing_leaders
    ON player_season_stats(dynasty_id, season, rushing_yards DESC);

CREATE INDEX idx_season_stats_receiving_leaders
    ON player_season_stats(dynasty_id, season, receiving_yards DESC);

CREATE INDEX idx_season_stats_player_lookup
    ON player_season_stats(dynasty_id, player_id, season);
```

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)

**1.1 Database Migration**
- Create migration script in `src/database/migrations/`
- Add `player_season_stats` table with indexes
- Test migration on fresh database

**1.2 Stats Aggregator Module**
- Create `src/statistics/season_aggregator.py`
- Implement `aggregate_game_stats(game_id, dynasty_id, season)` method
- Implement `recalculate_season_stats(dynasty_id, season, player_id=None)` method
- Use UPSERT pattern (INSERT ... ON CONFLICT DO UPDATE)

**1.3 Integration Point**
- Hook into `StoreManager.persist_game_result()` in `src/stores/store_manager.py`
- Call season aggregator after persisting game stats
- Ensure atomic transaction (game stats + season stats together)

### Phase 2: Stats API Updates (Week 1-2)

**2.1 New DatabaseAPI Methods**
- `get_season_passing_leaders()` - Query `player_season_stats` directly
- `get_season_rushing_leaders()` - Query `player_season_stats` directly
- `get_season_receiving_leaders()` - Query `player_season_stats` directly
- `get_player_season_stats(player_id, season)` - Single player lookup

**2.2 Keep Game-Level Queries**
- `get_player_game_log(player_id, season)` - Query `player_game_stats` for individual games
- Used for player detail pages showing game-by-game performance

**2.3 Update StatsAPI**
- Point leaderboard methods to new DatabaseAPI methods
- Remove complex filtering/aggregation from `ui/widgets/team_statistics_widget.py`
- Simplify LeaderboardBuilder to use pre-aggregated data

### Phase 3: Duplicate Player Handling (Week 2)

**3.1 Deduplication Strategy**
- Analyze duplicate player_ids in existing data
- Decide on canonical player identification:
  - Option A: Group by `player_name` (simple, works for now)
  - Option B: Create `player_master` table (future-proof)

**3.2 Aggregation Logic**
- Update season aggregator to handle duplicates:
  ```sql
  GROUP BY dynasty_id, player_name, season  -- Merges duplicate player_ids
  ```
- Use `MAX(team_id)` for most recent team
- Sum all stats across duplicate player_ids

**3.3 Validation**
- Add data quality checks: verify season totals match SUM(game stats)
- Log warnings for players with multiple player_ids

### Phase 4: Data Migration & Testing (Week 2)

**4.1 Backfill Existing Data**
- Create one-time migration script: `scripts/backfill_season_stats.py`
- For each existing dynasty/season, aggregate all player_game_stats
- Populate `player_season_stats` table
- Validate totals match

**4.2 Testing**
- Unit tests for season aggregator
- Integration tests for game simulation → stats persistence
- Performance benchmarks (compare old vs new query times)
- Test duplicate player handling

**4.3 UI Verification**
- Test Team Statistics widget shows correct season totals
- Test League Stats Leaders show correct rankings
- Verify no duplicate players in displays
- Test stats refresh after game simulation

### Phase 5: Cleanup & Optimization (Week 3)

**5.1 Remove Old Code**
- Remove complex aggregation logic from UI widgets
- Remove GROUP BY queries from old DatabaseAPI methods (keep for reference/fallback)
- Simplify LeaderboardBuilder

**5.2 Documentation**
- Update database schema docs
- Document season stats update flow
- Add comments explaining aggregation strategy

**5.3 Monitoring**
- Add logging for aggregation failures
- Track aggregation performance
- Monitor for data quality issues

## Update Flow

### After Each Game Simulation

```
1. Game simulated
   ↓
2. StoreManager.persist_game_result()
   ├─ Save to player_game_stats (existing)
   └─ Call SeasonAggregator.aggregate_game_stats()
       ↓
3. SeasonAggregator queries player_game_stats for season
   ↓
4. Calculate totals (SUM), computed stats (passer rating, etc.)
   ↓
5. UPSERT into player_season_stats
   ↓
6. Commit transaction
```

### Leaderboard Query (New)

```
1. UI requests passing leaders
   ↓
2. StatsAPI.get_passing_leaders()
   ↓
3. DatabaseAPI.get_season_passing_leaders()
   ↓
4. Simple SELECT from player_season_stats
   WHERE dynasty_id = ? AND season = ?
   ORDER BY passing_yards DESC
   LIMIT 25
   ↓
5. Return pre-computed results (instant!)
```

## Benefits

### Immediate
- **10-100x faster** leaderboard queries (no aggregation needed)
- **No duplicates** - players appear once with correct totals
- **Pre-computed metrics** - passer rating, yards per carry calculated once
- **Simpler UI code** - no filtering/deduplication needed

### Long-term
- **Scalable** - performance doesn't degrade with more games
- **Career stats** - easy to SUM across seasons
- **Historical comparisons** - season-to-season analysis
- **Foundation** for player master table and canonical IDs
- **Industry standard** pattern used by all major sports sites

### Data Quality
- **Validation** - can verify season totals match game-by-game sum
- **Deduplication** - handles duplicate player_ids gracefully
- **Audit trail** - `last_updated` timestamp for debugging
- **Flexibility** - can add computed stats without changing game stats

## Migration Strategy

### For New Dynasties
- Season stats table populated automatically during game simulation
- No action needed

### For Existing Dynasties
- Run backfill script once: `python scripts/backfill_season_stats.py`
- Script aggregates all existing `player_game_stats` → `player_season_stats`
- Validates totals match
- Safe to re-run (UPSERT pattern)

### Rollback Plan
- Keep old DatabaseAPI methods as fallback
- Can switch back by changing StatsAPI routing
- No data loss (game stats unchanged)

## Success Metrics

- [ ] Leaderboard queries < 10ms (vs 100-500ms currently)
- [ ] Zero duplicate players in UI
- [ ] Season totals match SUM(game stats) for all players
- [ ] Stats appear immediately after game simulation (with refresh fix)
- [ ] Support for 100+ seasons without performance degradation

## Future Enhancements

Once `player_season_stats` is stable, consider:

1. **Player Master Table** - Canonical player identities with career history
2. **Career Stats Aggregation** - `player_career_stats` table
3. **Split Stats** - Home/away, division, playoff splits
4. **Advanced Metrics** - EPA, DVOA, QBR (if simulation supports)
5. **Historical Rankings** - All-time leaders, single-season records

## References

- Database schema: `docs/schema/database_schema.md`
- Current stats API: `src/statistics/stats_api.py`
- Game persistence: `src/stores/store_manager.py`
- UI stats display: `ui/widgets/team_statistics_widget.py`
