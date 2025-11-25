# Statistics Preservation System Plan

**Status:** Draft
**Created:** 2025-01-26
**Author:** System Design
**Target:** Phase 1 completion by end of current development cycle

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [Architecture Overview](#architecture-overview)
4. [Core Components](#core-components)
5. [Database Schema](#database-schema)
6. [Implementation Phases](#implementation-phases)
7. [Testing Strategy](#testing-strategy)
8. [Integration Points](#integration-points)
9. [Performance Benchmarks](#performance-benchmarks)
10. [Migration Path](#migration-path)

---

## Executive Summary

This plan introduces a **Statistics Preservation System** to address long-term scalability concerns with the player statistics database. As dynasties progress through multiple seasons (10, 20, 50+ years), the `player_game_stats` and `games` tables will grow to millions of rows, causing query performance degradation.

**Solution:** Implement a **hot/cold storage architecture** with automatic archival:
- **Hot Storage:** Last 3 seasons with full game-level detail
- **Warm Storage:** All seasons with aggregated summaries (instant career stat queries)
- **Cold Storage:** Deleted game data for seasons beyond retention window

**Key Benefits:**
- ✅ Constant database size (~500 MB) regardless of dynasty length
- ✅ Lightning-fast career stat queries (pre-aggregated)
- ✅ Preserve complete historical records forever
- ✅ User-configurable retention policies
- ✅ Non-breaking changes to existing systems

---

## Problem Statement

### Current State

**Database Growth Without Archival:**

| Seasons | player_game_stats rows | games rows | Estimated DB Size | Query Performance |
|---------|------------------------|------------|-------------------|-------------------|
| 1       | ~272,000              | 272        | ~50 MB           | Fast             |
| 10      | ~2.7 million          | 2,720      | ~500 MB          | Moderate         |
| 50      | ~13.5 million         | 13,600     | ~2.5 GB          | Slow             |
| 100     | ~27 million           | 27,200     | ~5 GB            | Very Slow        |

**Problems:**
1. **Query Slowdown:** Career stat queries must join across all seasons
2. **Memory Usage:** Large result sets for simple queries
3. **Database Bloat:** SQLite file grows indefinitely
4. **No Retention Control:** All data kept forever (no user choice)

### Target State

**With Statistics Preservation System:**

| Seasons | Active Data | Archive Data | DB Size | Career Query Time |
|---------|-------------|--------------|---------|-------------------|
| 1       | 272K rows   | 0           | 50 MB   | <1ms             |
| 10      | 816K rows   | Summaries   | 80 MB   | <1ms             |
| 50      | 816K rows   | Summaries   | 150 MB  | <1ms             |
| 100     | 816K rows   | Summaries   | 300 MB  | <1ms             |

**Improvements:**
- ✅ Constant query performance (independent of dynasty age)
- ✅ Predictable database size
- ✅ Instant career stat lookups
- ✅ Complete historical context preserved

---

## Architecture Overview

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                    STATISTICS LAYER                          │
│                                                              │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │   StatsAPI       │────────▶│ DatabaseAPI      │         │
│  │  (Query Layer)   │         │ (Data Access)    │         │
│  └──────────────────┘         └──────────────────┘         │
│           │                            │                     │
│           ▼                            ▼                     │
│  ┌──────────────────────────────────────────────┐          │
│  │        StatisticsArchiver                     │          │
│  │    (Orchestration & Lifecycle)                │          │
│  │                                                │          │
│  │  ┌────────────────────────────────────────┐  │          │
│  │  │  SeasonAggregator                      │  │          │
│  │  │  - Aggregate game stats → season stats │  │          │
│  │  │  - Calculate season metrics            │  │          │
│  │  └────────────────────────────────────────┘  │          │
│  │                                                │          │
│  │  ┌────────────────────────────────────────┐  │          │
│  │  │  RetentionPolicyManager                │  │          │
│  │  │  - Evaluate retention rules            │  │          │
│  │  │  - Determine what to archive           │  │          │
│  │  └────────────────────────────────────────┘  │          │
│  │                                                │          │
│  │  ┌────────────────────────────────────────┐  │          │
│  │  │  ArchivalValidator                     │  │          │
│  │  │  - Verify data integrity               │  │          │
│  │  │  - Validate aggregations               │  │          │
│  │  └────────────────────────────────────────┘  │          │
│  └──────────────────────────────────────────────┘          │
│           │                                                  │
│           ▼                                                  │
│  ┌──────────────────────────────────────────────┐          │
│  │        Database Layer                         │          │
│  │                                                │          │
│  │  [player_game_stats]  ← Hot storage          │          │
│  │  [games]              ← Hot storage          │          │
│  │                                                │          │
│  │  [player_season_stats] ← Warm storage        │          │
│  │  [season_archives]     ← Warm storage        │          │
│  │  [archival_config]     ← Config              │          │
│  └──────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Single Responsibility:** Each class has ONE clear purpose
2. **Dependency Injection:** All dependencies passed via constructor (testable)
3. **Interface-Based:** Define protocols/interfaces for each component
4. **Immutable Configuration:** Archival config loaded once, cached
5. **Transaction Safety:** All archival operations wrapped in transactions
6. **Validation First:** Verify data integrity before and after archival
7. **Non-Destructive:** Never delete data without validation checks

---

## Core Components

### 1. StatisticsArchiver (Main Orchestrator)

**Location:** `src/statistics/statistics_archiver.py`

**Responsibility:** Orchestrate the entire archival process during season transitions.

**Key Methods:**

```python
class StatisticsArchiver:
    """
    Main orchestrator for statistics preservation and archival.

    Coordinates season aggregation, retention policy enforcement,
    and historical data management.
    """

    def __init__(
        self,
        database_path: str,
        dynasty_id: str,
        aggregator: Optional[SeasonAggregator] = None,
        policy_manager: Optional[RetentionPolicyManager] = None,
        validator: Optional[ArchivalValidator] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize archiver with dependency injection for testability.

        Args:
            database_path: Path to SQLite database
            dynasty_id: Dynasty identifier
            aggregator: Optional custom aggregator (for testing)
            policy_manager: Optional custom policy manager (for testing)
            validator: Optional custom validator (for testing)
            logger: Optional logger instance
        """
        self.database_path = database_path
        self.dynasty_id = dynasty_id
        self.logger = logger or logging.getLogger(self.__class__.__name__)

        # Dependency injection with defaults
        self.aggregator = aggregator or SeasonAggregator(database_path, dynasty_id)
        self.policy_manager = policy_manager or RetentionPolicyManager(database_path, dynasty_id)
        self.validator = validator or ArchivalValidator(database_path, dynasty_id)

    def archive_season(self, completed_season: int) -> ArchivalResult:
        """
        Archive a completed season (called during PLAYOFFS → OFFSEASON transition).

        Process:
        1. Validate season is complete
        2. Aggregate game stats → season summaries
        3. Create season archive record
        4. Apply retention policy
        5. Validate post-archival integrity

        Args:
            completed_season: Season year that just finished (e.g., 2025)

        Returns:
            ArchivalResult with status, metrics, and any errors

        Raises:
            ArchivalValidationError: If pre/post validation fails
            ArchivalTransactionError: If database transaction fails
        """

    def get_archival_status(self) -> Dict[str, Any]:
        """
        Get current archival status for this dynasty.

        Returns:
            {
                'active_seasons': int,  # Seasons in hot storage
                'archived_seasons': int,  # Seasons in cold storage
                'total_seasons': int,
                'retention_policy': str,
                'retention_seasons': int,
                'last_archival': datetime,
                'database_size_mb': float,
                'game_stats_count': int,
                'season_summaries_count': int
            }
        """

    def update_retention_policy(
        self,
        retention_seasons: int,
        apply_immediately: bool = False
    ) -> None:
        """
        Update retention policy for this dynasty.

        Args:
            retention_seasons: Number of seasons to keep in hot storage
            apply_immediately: If True, apply new policy now (triggers archival)
        """
```

**Why This Design:**
- ✅ **Testable:** All dependencies injected, can mock database
- ✅ **Single Entry Point:** One method (`archive_season`) for all archival
- ✅ **Clear Lifecycle:** Validates → Aggregates → Archives → Validates
- ✅ **Error Handling:** Returns structured result, doesn't crash season transition

---

### 2. SeasonAggregator (Data Transformation)

**Location:** `src/statistics/season_aggregator.py`

**Responsibility:** Aggregate game-level statistics into season summaries.

**Key Methods:**

```python
class SeasonAggregator:
    """
    Aggregate game-level statistics into season summaries.

    Handles the mathematical aggregation of player stats from individual
    games into season totals, with calculated metrics (passer rating, etc.).
    """

    def __init__(
        self,
        database_path: str,
        dynasty_id: str,
        database_api: Optional[DatabaseAPI] = None
    ):
        """Initialize aggregator with database connection."""

    def aggregate_player_season_stats(
        self,
        season: int
    ) -> List[PlayerSeasonStats]:
        """
        Aggregate all player stats for a season.

        Process:
        1. Query all player_game_stats for season
        2. Group by player_id
        3. Sum counting stats (yards, TDs, etc.)
        4. Calculate derived metrics (passer rating, YPC, catch rate)
        5. Return list of PlayerSeasonStats objects

        Args:
            season: Season year to aggregate

        Returns:
            List of PlayerSeasonStats dataclasses
        """

    def aggregate_team_season_stats(
        self,
        season: int
    ) -> List[TeamSeasonStats]:
        """
        Aggregate team-level stats for a season.

        Args:
            season: Season year to aggregate

        Returns:
            List of TeamSeasonStats dataclasses
        """

    def create_season_archive(
        self,
        season: int,
        super_bowl_champion: int,
        awards: Dict[str, str]
    ) -> SeasonArchive:
        """
        Create season archive record with champions and awards.

        Args:
            season: Season year
            super_bowl_champion: Team ID of champion
            awards: Dict of award name → player_id

        Returns:
            SeasonArchive dataclass
        """
```

**Why This Design:**
- ✅ **Pure Functions:** No side effects, just data transformation
- ✅ **Easily Testable:** Input game stats, output season stats
- ✅ **Type-Safe:** Uses dataclasses for clear contracts
- ✅ **Reusable:** Can aggregate any season, not tied to archival

---

### 3. RetentionPolicyManager (Business Logic)

**Location:** `src/statistics/retention_policy_manager.py`

**Responsibility:** Evaluate retention policies and determine what to archive.

**Key Methods:**

```python
class RetentionPolicyManager:
    """
    Manage retention policies for historical data.

    Determines which seasons should be kept in hot storage vs archived.
    Supports per-dynasty configuration.
    """

    def __init__(
        self,
        database_path: str,
        dynasty_id: str
    ):
        """Initialize policy manager."""

    def get_retention_policy(self) -> RetentionPolicy:
        """
        Get retention policy for this dynasty.

        Returns:
            RetentionPolicy dataclass with:
            - policy_type: 'keep_all' | 'keep_n_seasons' | 'summary_only'
            - retention_seasons: Number of seasons to keep
            - auto_archive: Whether to automatically archive
        """

    def should_archive_season(
        self,
        season: int,
        current_season: int
    ) -> bool:
        """
        Determine if a season should be archived.

        Args:
            season: Season year to check
            current_season: Current season year

        Returns:
            True if season exceeds retention window
        """

    def get_seasons_to_archive(
        self,
        current_season: int
    ) -> List[int]:
        """
        Get list of seasons that should be archived.

        Args:
            current_season: Current season year

        Returns:
            List of season years to archive
        """

    def update_policy(
        self,
        retention_seasons: int,
        auto_archive: bool = True
    ) -> None:
        """
        Update retention policy in database.

        Args:
            retention_seasons: Number of seasons to keep
            auto_archive: Whether to auto-archive on season end
        """
```

**Why This Design:**
- ✅ **Configurable:** Per-dynasty policies
- ✅ **Clear Logic:** One method to check if season should archive
- ✅ **Extensible:** Easy to add new policy types
- ✅ **Testable:** Pure logic, no complex dependencies

---

### 4. ArchivalValidator (Data Integrity)

**Location:** `src/statistics/archival_validator.py`

**Responsibility:** Validate data integrity before and after archival operations.

**Key Methods:**

```python
class ArchivalValidator:
    """
    Validate data integrity for archival operations.

    Ensures that aggregated stats match game-level stats, and that
    archival operations don't corrupt or lose data.
    """

    def __init__(
        self,
        database_path: str,
        dynasty_id: str
    ):
        """Initialize validator."""

    def validate_pre_archival(
        self,
        season: int
    ) -> ValidationResult:
        """
        Validate season data before archival.

        Checks:
        - Season is complete (all games played)
        - Game stats exist in database
        - No duplicate records
        - Data is consistent (no negative stats, etc.)

        Args:
            season: Season year to validate

        Returns:
            ValidationResult with pass/fail and any errors
        """

    def validate_aggregation(
        self,
        season: int,
        aggregated_stats: List[PlayerSeasonStats]
    ) -> ValidationResult:
        """
        Validate that aggregated stats match game-level stats.

        Process:
        1. Query game-level stats for season
        2. Manually sum for each player
        3. Compare with aggregated stats
        4. Flag any mismatches

        Args:
            season: Season year
            aggregated_stats: List of aggregated PlayerSeasonStats

        Returns:
            ValidationResult with detailed comparison
        """

    def validate_post_archival(
        self,
        season: int,
        archived: bool
    ) -> ValidationResult:
        """
        Validate data integrity after archival.

        Checks:
        - Season summaries exist
        - Game data properly marked/deleted
        - Career stats still queryable
        - No data corruption

        Args:
            season: Season year
            archived: Whether game data was deleted

        Returns:
            ValidationResult with integrity status
        """
```

**Why This Design:**
- ✅ **Safety Net:** Catches data corruption before it happens
- ✅ **Detailed Reports:** Returns structured validation results
- ✅ **Independent:** Can run validation without triggering archival
- ✅ **Testable:** Clear inputs/outputs, easy to unit test

---

### 5. Data Models (Type Safety)

**Location:** `src/statistics/models.py`

```python
from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import datetime

@dataclass
class PlayerSeasonStats:
    """Aggregated player statistics for a single season."""
    dynasty_id: str
    player_id: str
    season: int
    team_id: int
    position: str
    games_played: int
    games_started: int

    # Passing
    passing_yards: int = 0
    passing_tds: int = 0
    passing_completions: int = 0
    passing_attempts: int = 0
    interceptions: int = 0

    # Rushing
    rushing_yards: int = 0
    rushing_tds: int = 0
    rushing_attempts: int = 0

    # Receiving
    receiving_yards: int = 0
    receiving_tds: int = 0
    receptions: int = 0
    targets: int = 0

    # Defense
    tackles_total: int = 0
    sacks: float = 0.0
    interceptions_def: int = 0

    # Calculated metrics
    passer_rating: Optional[float] = None
    yards_per_carry: Optional[float] = None
    catch_rate: Optional[float] = None

    # Awards
    awards: List[str] = None  # ["MVP", "Pro Bowl", "All-Pro"]

@dataclass
class SeasonArchive:
    """Metadata for an archived season."""
    dynasty_id: str
    season: int
    super_bowl_champion: int
    afc_champion: int
    nfc_champion: int
    mvp_player_id: str
    offensive_poy: str
    defensive_poy: str
    archived_at: datetime

@dataclass
class RetentionPolicy:
    """Retention policy configuration."""
    dynasty_id: str
    policy_type: str  # 'keep_all' | 'keep_n_seasons' | 'summary_only'
    retention_seasons: int
    auto_archive: bool

@dataclass
class ArchivalResult:
    """Result of an archival operation."""
    success: bool
    season: int
    player_stats_aggregated: int
    game_stats_archived: int
    games_archived: int
    validation_passed: bool
    errors: List[str]
    duration_seconds: float

@dataclass
class ValidationResult:
    """Result of a validation check."""
    passed: bool
    errors: List[str]
    warnings: List[str]
    details: Dict[str, any]
```

**Why This Design:**
- ✅ **Type Safety:** Catch bugs at development time
- ✅ **Documentation:** Clear contracts for all data structures
- ✅ **IDE Support:** Autocomplete and type checking
- ✅ **Immutable:** Dataclasses are immutable by default

---

## Database Schema

### New Tables

#### 1. player_season_stats (Warm Storage)

```sql
CREATE TABLE player_season_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    player_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    position TEXT NOT NULL,

    -- Games played
    games_played INTEGER DEFAULT 0,
    games_started INTEGER DEFAULT 0,

    -- Passing stats (aggregated)
    passing_yards INTEGER DEFAULT 0,
    passing_tds INTEGER DEFAULT 0,
    passing_completions INTEGER DEFAULT 0,
    passing_attempts INTEGER DEFAULT 0,
    interceptions INTEGER DEFAULT 0,

    -- Rushing stats (aggregated)
    rushing_yards INTEGER DEFAULT 0,
    rushing_tds INTEGER DEFAULT 0,
    rushing_attempts INTEGER DEFAULT 0,

    -- Receiving stats (aggregated)
    receiving_yards INTEGER DEFAULT 0,
    receiving_tds INTEGER DEFAULT 0,
    receptions INTEGER DEFAULT 0,
    targets INTEGER DEFAULT 0,

    -- Defense stats (aggregated)
    tackles_total INTEGER DEFAULT 0,
    sacks REAL DEFAULT 0.0,
    interceptions_def INTEGER DEFAULT 0,

    -- Special teams stats (aggregated)
    field_goals_made INTEGER DEFAULT 0,
    field_goals_attempted INTEGER DEFAULT 0,
    extra_points_made INTEGER DEFAULT 0,
    extra_points_attempted INTEGER DEFAULT 0,

    -- Calculated metrics (stored for speed)
    passer_rating REAL,
    yards_per_carry REAL,
    catch_rate REAL,
    yards_per_reception REAL,

    -- Awards and honors (JSON array)
    awards TEXT,  -- JSON: ["MVP", "Pro Bowl", "All-Pro First Team"]

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, player_id, season)
);

-- Indexes for fast queries
CREATE INDEX idx_player_season_stats_dynasty ON player_season_stats(dynasty_id);
CREATE INDEX idx_player_season_stats_player ON player_season_stats(player_id);
CREATE INDEX idx_player_season_stats_season ON player_season_stats(season);
CREATE INDEX idx_player_season_stats_team ON player_season_stats(team_id);
CREATE INDEX idx_player_season_stats_position ON player_season_stats(position);
```

#### 2. season_archives (Season Metadata)

```sql
CREATE TABLE season_archives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,

    -- Champions
    super_bowl_champion INTEGER,  -- team_id
    afc_champion INTEGER,
    nfc_champion INTEGER,

    -- Individual awards
    mvp_player_id TEXT,
    offensive_poy TEXT,
    defensive_poy TEXT,
    offensive_rookie_of_year TEXT,
    defensive_rookie_of_year TEXT,
    comeback_player TEXT,
    coach_of_year INTEGER,  -- team_id

    -- Season records (JSON)
    season_records TEXT,  -- JSON: {"most_passing_yards": {"player": "QB_1", "value": 5477}, ...}

    -- Team records
    best_record_team_id INTEGER,
    best_record_wins INTEGER,
    best_record_losses INTEGER,

    -- Metadata
    games_played INTEGER DEFAULT 272,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, season),

    -- Foreign keys for champions/awards
    FOREIGN KEY (super_bowl_champion) REFERENCES teams(team_id),
    FOREIGN KEY (afc_champion) REFERENCES teams(team_id),
    FOREIGN KEY (nfc_champion) REFERENCES teams(team_id)
);

-- Indexes
CREATE INDEX idx_season_archives_dynasty ON season_archives(dynasty_id);
CREATE INDEX idx_season_archives_season ON season_archives(season);
CREATE INDEX idx_season_archives_champion ON season_archives(super_bowl_champion);
```

#### 3. archival_config (Dynasty Configuration)

```sql
CREATE TABLE archival_config (
    dynasty_id TEXT PRIMARY KEY,

    -- Policy configuration
    policy_type TEXT DEFAULT 'keep_n_seasons',  -- 'keep_all' | 'keep_n_seasons' | 'summary_only'
    retention_seasons INTEGER DEFAULT 3,  -- Number of seasons to keep in hot storage
    auto_archive BOOLEAN DEFAULT TRUE,  -- Automatically archive on season end

    -- Statistics
    last_archival_season INTEGER,  -- Last season that was archived
    last_archival_timestamp TIMESTAMP,
    total_seasons_archived INTEGER DEFAULT 0,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,

    CHECK (policy_type IN ('keep_all', 'keep_n_seasons', 'summary_only')),
    CHECK (retention_seasons >= 0),
    CHECK (retention_seasons <= 100)  -- Sanity check
);
```

### Schema Changes to Existing Tables

#### 4. Add archival flags to existing tables

```sql
-- Mark games as archived
ALTER TABLE games ADD COLUMN archived BOOLEAN DEFAULT FALSE;
CREATE INDEX idx_games_archived ON games(archived);

-- Mark player game stats as archived
ALTER TABLE player_game_stats ADD COLUMN archived BOOLEAN DEFAULT FALSE;
CREATE INDEX idx_player_game_stats_archived ON player_game_stats(archived);
```

**Migration Strategy:** These columns default to FALSE, so existing data is unaffected.

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Goal:** Implement core classes and database schema without integration.

**Tasks:**
1. ✅ Create data models (`models.py`)
2. ✅ Create database migration scripts
3. ✅ Implement `SeasonAggregator` class
4. ✅ Implement `RetentionPolicyManager` class
5. ✅ Implement `ArchivalValidator` class
6. ✅ Implement `StatisticsArchiver` class
7. ✅ Write unit tests for each class

**Deliverables:**
- All classes implemented and tested
- Database schema migrated
- 80%+ test coverage
- No integration with season cycle yet

**Testing:**
```python
# Test aggregation accuracy
def test_season_aggregator_accuracy():
    # Insert 10 games worth of stats
    # Aggregate season
    # Verify totals match sum of games

# Test retention policy logic
def test_retention_policy_identifies_old_seasons():
    # Set retention to 3 seasons
    # Current season = 2030
    # Assert seasons 2026 and earlier should archive

# Test validation catches errors
def test_validator_detects_incomplete_season():
    # Create season with only 200 games
    # Run validation
    # Assert validation fails with clear error
```

---

### Phase 2: Integration (Week 3)

**Goal:** Integrate archiver into season cycle without enabling archival.

**Tasks:**
1. ✅ Add hook in `_transition_to_offseason()` to call archiver
2. ✅ Log archival results (don't actually archive yet)
3. ✅ Test with full season simulation
4. ✅ Verify aggregation matches game data

**Integration Point:**

```python
# src/season/season_cycle_controller.py
def _transition_to_offseason(self):
    """Execute transition from playoffs to offseason."""
    # ... existing code ...

    # NEW: Archive season statistics
    try:
        from statistics.statistics_archiver import StatisticsArchiver

        archiver = StatisticsArchiver(
            database_path=self.database_path,
            dynasty_id=self.dynasty_id
        )

        # Archive completed season
        result = archiver.archive_season(self.season_year)

        if result.success:
            self.logger.info(
                f"✅ Season {self.season_year} archived successfully:\n"
                f"  - Player stats aggregated: {result.player_stats_aggregated}\n"
                f"  - Game stats archived: {result.game_stats_archived}\n"
                f"  - Duration: {result.duration_seconds:.2f}s"
            )
        else:
            self.logger.error(
                f"❌ Season {self.season_year} archival failed:\n"
                f"  - Errors: {result.errors}"
            )
    except Exception as e:
        self.logger.error(f"Archival error: {e}")
        # Don't block offseason transition on archival failure
```

**Deliverables:**
- Archiver called during offseason transition
- Full integration tests pass
- Performance benchmarks recorded

---

### Phase 3: Archival Enabled (Week 4)

**Goal:** Enable actual archival with retention policy enforcement.

**Tasks:**
1. ✅ Enable game data deletion for old seasons
2. ✅ Update StatsAPI to query season summaries for career stats
3. ✅ Add UI indicators for archived seasons
4. ✅ Test multi-season archival (simulate 10 seasons)

**StatsAPI Changes:**

```python
# src/statistics/stats_api.py
class StatsAPI:
    def get_player_career_stats(
        self,
        player_id: str
    ) -> Dict[str, Any]:
        """
        Get career stats across all seasons (NEW METHOD).

        Queries player_season_stats table for fast aggregation.
        """
        query = """
            SELECT
                SUM(passing_yards) as career_passing_yards,
                SUM(passing_tds) as career_passing_tds,
                SUM(rushing_yards) as career_rushing_yards,
                SUM(rushing_tds) as career_rushing_tds,
                COUNT(DISTINCT season) as seasons_played,
                MIN(season) as rookie_season,
                MAX(season) as last_season
            FROM player_season_stats
            WHERE player_id = ? AND dynasty_id = ?
        """

    def get_player_season_history(
        self,
        player_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get season-by-season breakdown for player (NEW METHOD).

        Returns list of seasons with stats and awards.
        """
        query = """
            SELECT
                season,
                team_id,
                games_played,
                passing_yards,
                passing_tds,
                rushing_yards,
                receiving_yards,
                awards
            FROM player_season_stats
            WHERE player_id = ? AND dynasty_id = ?
            ORDER BY season ASC
        """
```

**Deliverables:**
- Archival fully functional
- Career stats queries work correctly
- UI shows archived season indicators
- Performance improvement verified

---

### Phase 4: Polish & Optimization (Week 5)

**Goal:** Add user-facing features and optimizations.

**Tasks:**
1. ✅ Add UI for configuring retention policy
2. ✅ Add "View Archived Seasons" feature
3. ✅ Add manual archival trigger (for testing/recovery)
4. ✅ Performance optimization (query caching, indexes)
5. ✅ Add archival statistics dashboard

**UI Features:**

```
Dynasty Settings → Statistics Archival
┌─────────────────────────────────────────────┐
│ Retention Policy                             │
│                                              │
│ Keep last [ 3 ] seasons in full detail      │
│                                              │
│ ☑ Automatically archive on season end       │
│                                              │
│ Current Status:                              │
│ - Active seasons: 3 (2028, 2029, 2030)      │
│ - Archived seasons: 7 (2021-2027)           │
│ - Database size: 124 MB                      │
│ - Last archival: 2025-01-25                  │
│                                              │
│ [Save Settings]  [Manual Archive Now]        │
└─────────────────────────────────────────────┘
```

**Deliverables:**
- Complete user control over archival
- Documentation for end users
- Performance benchmarks published

---

## Testing Strategy

### Unit Tests

**Target:** 90%+ code coverage

```python
# tests/statistics/test_season_aggregator.py
class TestSeasonAggregator:
    def test_aggregate_player_stats_accuracy(self):
        """Verify aggregated stats match sum of game stats."""

    def test_aggregate_handles_empty_season(self):
        """Handle season with no games gracefully."""

    def test_calculated_metrics_correct(self):
        """Verify passer rating, YPC calculations."""

# tests/statistics/test_retention_policy_manager.py
class TestRetentionPolicyManager:
    def test_identifies_seasons_to_archive(self):
        """Correctly identify seasons beyond retention window."""

    def test_respects_keep_all_policy(self):
        """Never archive when policy is keep_all."""

    def test_handles_first_season(self):
        """Don't archive when only 1 season exists."""

# tests/statistics/test_archival_validator.py
class TestArchivalValidator:
    def test_detects_incomplete_season(self):
        """Fail validation if season has < 272 games."""

    def test_detects_aggregation_mismatch(self):
        """Fail if aggregated stats don't match game totals."""

    def test_post_archival_integrity(self):
        """Verify data intact after archival."""
```

### Integration Tests

```python
# tests/statistics/test_statistics_archiver_integration.py
class TestStatisticsArchiverIntegration:
    def test_full_archival_workflow(self):
        """
        Test complete archival process:
        1. Simulate 5 seasons
        2. Archive seasons 1-2
        3. Verify season summaries exist
        4. Verify game data deleted
        5. Verify career stats still work
        """

    def test_multi_season_archival(self):
        """Simulate 10 seasons, verify performance."""

    def test_archival_rollback_on_error(self):
        """Verify transaction rollback if validation fails."""
```

### Performance Benchmarks

```python
# tests/statistics/test_archival_performance.py
class TestArchivalPerformance:
    def test_career_stats_query_speed(self):
        """
        Compare query times:
        - Before archival (join across 10 seasons)
        - After archival (query pre-aggregated summaries)

        Target: 10x+ improvement
        """

    def test_database_size_growth(self):
        """
        Verify database size stays constant:
        - 1 season: ~50 MB
        - 10 seasons: ~80 MB (not 500 MB!)
        - 50 seasons: ~150 MB (not 2.5 GB!)
        """
```

---

## Integration Points

### 1. SeasonCycleController (Primary Integration)

**File:** `src/season/season_cycle_controller.py`

**Method:** `_transition_to_offseason()`

**Integration:**
```python
def _transition_to_offseason(self):
    # ... existing Super Bowl handling ...

    # Archive season statistics
    if self.enable_persistence:
        self._archive_season_statistics()

    # ... rest of offseason transition ...

def _archive_season_statistics(self):
    """Archive completed season during offseason transition."""
    try:
        from statistics.statistics_archiver import StatisticsArchiver

        archiver = StatisticsArchiver(
            database_path=self.database_path,
            dynasty_id=self.dynasty_id,
            logger=self.logger
        )

        result = archiver.archive_season(self.season_year)

        if not result.success:
            self.logger.warning(
                f"Season archival completed with errors: {result.errors}"
            )
    except Exception as e:
        self.logger.error(f"Season archival failed: {e}", exc_info=True)
        # Don't block offseason transition on archival failure
```

### 2. StatsAPI (Query Layer)

**File:** `src/statistics/stats_api.py`

**New Methods:**
- `get_player_career_stats()` - Query season summaries
- `get_player_season_history()` - Season-by-season breakdown
- `get_season_awards()` - Awards for specific season
- `get_season_champions()` - Champions for specific season

### 3. UI Layer (Player Profiles)

**File:** `ui/views/player_profile_view.py` (future)

**Changes:**
- Add "Career Stats" tab (queries season summaries)
- Add "Season History" tab (shows year-by-year)
- Add "Archived" indicator for old game logs
- Add note: "Game logs available for seasons 2028-2030 only"

---

## Performance Benchmarks

### Expected Performance Improvements

| Operation | Before Archival | After Archival | Improvement |
|-----------|----------------|----------------|-------------|
| Career stats query (10 seasons) | ~150ms | <5ms | 30x faster |
| Career stats query (50 seasons) | ~800ms | <5ms | 160x faster |
| Database size (10 seasons) | 500 MB | 80 MB | 84% smaller |
| Database size (50 seasons) | 2.5 GB | 150 MB | 94% smaller |
| Current season queries | 50ms | 20ms | 2.5x faster |

### Benchmark Tests

```python
# tests/statistics/benchmarks.py
def benchmark_career_stats_query():
    """
    Setup:
    - Create 50 seasons of player data
    - One player with stats every game

    Measure:
    - Query time WITHOUT archival (join across 50 seasons)
    - Query time WITH archival (query season_stats table)

    Expected:
    - 100x+ speedup with archival
    """
```

---

## Migration Path

### For Existing Dynasties

**Challenge:** Existing dynasties have game data but no season summaries.

**Solution:** One-time migration script

```python
# scripts/migrate_existing_dynasty_to_archival.py
def migrate_dynasty_to_archival(dynasty_id: str):
    """
    Migrate existing dynasty to use archival system.

    Process:
    1. Identify all completed seasons in database
    2. For each season:
       a) Aggregate game stats → season summaries
       b) Create season archive record
       c) Mark old games as archived (don't delete yet)
    3. Create archival config for dynasty
    4. Validate migration

    Safe: Doesn't delete any data, only creates summaries.
    """
```

**User Experience:**
- First time running new version: "Preparing historical stats... (one-time process)"
- Migration runs in background
- Game data not deleted until explicitly enabled

---

## Future Enhancements

### Phase 5: Advanced Features (Future)

1. **Export Archive to JSON**
   - Export old seasons to JSON files
   - Compress with gzip
   - Load on-demand for viewing

2. **Award Voting System**
   - Calculate MVP votes based on stats
   - Track OPOY/DPOY candidates
   - Historical award tracking

3. **Historical Records Tracking**
   - Track all-time records (most passing yards in a season, etc.)
   - Compare current players to historical greats
   - "Hall of Fame" eligibility tracking

4. **Advanced Analytics**
   - Career trajectory analysis
   - Peak season identification
   - Statistical comparisons across eras

---

## Success Criteria

### Must Have (MVP):
- ✅ Season summaries automatically created on offseason transition
- ✅ Retention policy enforced (keep last 3 seasons by default)
- ✅ Career stats queries work correctly
- ✅ Database size stays under 200 MB for 50+ season dynasties
- ✅ 90%+ test coverage
- ✅ No data loss or corruption

### Should Have:
- ✅ User-configurable retention policy
- ✅ Manual archival trigger
- ✅ Archival status dashboard
- ✅ Performance benchmarks documented

### Nice to Have:
- ☐ Export archive to JSON
- ☐ Award voting system
- ☐ Historical records tracking

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Data corruption during archival | HIGH | Pre/post validation checks, transaction rollback |
| Performance degradation | MEDIUM | Benchmark testing, query optimization |
| Breaking existing queries | HIGH | Backward compatibility, phased rollout |
| User confusion | LOW | Clear UI indicators, documentation |
| Aggregation errors | MEDIUM | Validation against game totals |

---

## Conclusion

This statistics preservation system provides a **scalable, maintainable, and testable** solution to long-term dynasty data management. By using a modular architecture with clear separation of concerns, we can:

1. ✅ **Maintain constant performance** regardless of dynasty age
2. ✅ **Preserve complete historical records** forever
3. ✅ **Give users control** over retention policies
4. ✅ **Test thoroughly** with isolated unit tests
5. ✅ **Integrate cleanly** with minimal changes to existing systems

The phased implementation approach allows incremental delivery while maintaining stability of the existing system.

---

**Next Steps:**
1. Review and approve plan
2. Begin Phase 1 implementation
3. Set up test infrastructure
4. Create milestone tracking for each phase