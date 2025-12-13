# Milestone #10: Awards System

**Status**: 🟡 In Progress (Tollgates 1-6 Complete, 168 tests passing)
**Dependencies**: ✅ Statistics (#2), ✅ Team Statistics (#8), ⚠️ Analytics (#3 - grading system exists)

---

## Vision

Implement a comprehensive NFL Awards System that recognizes exceptional player performance with realistic end-of-season awards, All-Pro/Pro Bowl selections, and statistical leader tracking. Create historical records and legacy moments that enhance dynasty depth and player prestige.

---

## Executive Summary

The Awards System adds realistic year-end recognition through:
- **8 Major Awards**: MVP, OPOY, DPOY, OROY, DROY, CPOY, COY, EOY
- **All-Pro Teams**: 44 players (First Team + Second Team)
- **Pro Bowl**: AFC/NFC rosters with starters/reserves
- **Statistical Leaders**: Top 10 in 15+ categories
- **Voting Simulation**: 50 media voters with archetypes and realistic variance

**Key Finding**: All infrastructure dependencies are complete. The existing grading system (`AnalyticsAPI`) provides play/game/season-level grades with EPA tracking—everything needed for realistic award voting.

**Implementation Strategy**: 7 tollgates over 4-6 weeks

---

## Architecture Overview

### Service Layer Pattern
```
Game Cycle Handler (Offseason)
    ↓
AwardsService (orchestrator)
    ├── AwardCriteria (scoring algorithms)
    ├── VotingEngine (50-voter simulation)
    └── AwardsAPI (database operations)
        ↓
    StatsAPI, AnalyticsAPI, TeamHistoryAPI (existing)
```

### Database Schema (6 New Tables)

1. **award_definitions** - Pre-populated award metadata (8 awards)
2. **award_winners** - Top 5 vote-getters per award
3. **award_nominees** - Top 10 candidates with stats snapshot
4. **all_pro_selections** - 44 players (22 first + 22 second team)
5. **pro_bowl_selections** - AFC/NFC rosters
6. **statistical_leaders** - Top 10 per category

All tables include `dynasty_id` for dynasty isolation.

---

## Tollgate Breakdown

### **Tollgate 1: Database Foundation** ✅
**Duration**: 3-4 days
**Objective**: Create all database tables, indexes, and AwardsAPI

#### Files to Create
- `src/game_cycle/database/awards_api.py` (350+ lines)
  - 17 CRUD methods for 6 tables
  - Follows `GameCycleDatabase` pattern
  - Returns typed dictionaries/lists

#### Files to Modify
- `src/game_cycle/database/schema.sql` - Add 6 tables
- `src/game_cycle/database/full_schema.sql` - Add 6 tables

#### Database Schema

**1. award_definitions** (pre-populated with 8 awards)
```sql
CREATE TABLE IF NOT EXISTS award_definitions (
    award_id TEXT PRIMARY KEY,  -- 'mvp', 'opoy', 'dpoy', 'oroy', 'droy', 'cpoy', 'coy', 'eoy'
    award_name TEXT NOT NULL,
    award_type TEXT NOT NULL CHECK(award_type IN ('INDIVIDUAL', 'ALL_PRO', 'PRO_BOWL')),
    category TEXT CHECK(category IN ('OFFENSE', 'DEFENSE', 'SPECIAL_TEAMS', 'COACHING', 'MANAGEMENT')),
    description TEXT,
    eligible_positions TEXT,  -- JSON array (NULL = all positions)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**2. award_winners** (top 5 vote-getters)
```sql
CREATE TABLE IF NOT EXISTS award_winners (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    award_id TEXT NOT NULL,
    player_id INTEGER,
    team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
    vote_points INTEGER,    -- Total weighted points (10-5-3-2-1 system)
    vote_share REAL,        -- Percentage of possible points (0.0-1.0)
    rank INTEGER,           -- 1 = winner, 2-5 = finalists
    is_winner BOOLEAN DEFAULT FALSE,
    voting_date DATE,
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    FOREIGN KEY (award_id) REFERENCES award_definitions(award_id),
    UNIQUE(dynasty_id, season, award_id, rank)
);
```

**3. award_nominees** (top 10 candidates)
```sql
CREATE TABLE IF NOT EXISTS award_nominees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    award_id TEXT NOT NULL,
    player_id INTEGER,
    team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
    nomination_rank INTEGER,
    stats_snapshot TEXT,    -- JSON of key stats
    grade_snapshot REAL,    -- Overall grade at nomination
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, season, award_id, player_id)
);
```

**4. all_pro_selections** (44 players total)
```sql
CREATE TABLE IF NOT EXISTS all_pro_selections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
    position TEXT NOT NULL,
    team_type TEXT NOT NULL CHECK(team_type IN ('FIRST_TEAM', 'SECOND_TEAM')),
    vote_points INTEGER,
    vote_share REAL,
    selection_date DATE,
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, season, position, team_type, player_id)
);
```

**5. pro_bowl_selections** (AFC/NFC rosters)
```sql
CREATE TABLE IF NOT EXISTS pro_bowl_selections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
    conference TEXT NOT NULL CHECK(conference IN ('AFC', 'NFC')),
    position TEXT NOT NULL,
    selection_type TEXT NOT NULL CHECK(selection_type IN ('STARTER', 'RESERVE', 'ALTERNATE')),
    combined_score REAL,  -- Fan (40%) + Coach (20%) + Player (40%)
    selection_date DATE,
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, season, conference, position, selection_type, player_id)
);
```

**6. statistical_leaders** (top 10 per category)
```sql
CREATE TABLE IF NOT EXISTS statistical_leaders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    stat_category TEXT NOT NULL,  -- 'passing_yards', 'rushing_yards', 'sacks', etc.
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
    position TEXT NOT NULL,
    stat_value INTEGER NOT NULL,
    league_rank INTEGER NOT NULL,
    recorded_date DATE,
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, season, stat_category, league_rank)
);
```

**Indexes for Performance**
```sql
CREATE INDEX IF NOT EXISTS idx_award_winners_dynasty_season ON award_winners(dynasty_id, season);
CREATE INDEX IF NOT EXISTS idx_award_winners_player ON award_winners(dynasty_id, player_id);
CREATE INDEX IF NOT EXISTS idx_all_pro_dynasty_season ON all_pro_selections(dynasty_id, season);
CREATE INDEX IF NOT EXISTS idx_all_pro_player ON all_pro_selections(dynasty_id, player_id);
CREATE INDEX IF NOT EXISTS idx_pro_bowl_dynasty_season ON pro_bowl_selections(dynasty_id, season);
CREATE INDEX IF NOT EXISTS idx_stat_leaders_dynasty_season ON statistical_leaders(dynasty_id, season);
```

#### AwardsAPI Methods (17 total)
```python
class AwardsAPI:
    # Award Winners
    def insert_award_winner(dynasty_id, season, award_id, player_id, team_id,
                          vote_points, vote_share, rank, is_winner)
    def get_award_winners(dynasty_id, season, award_id=None) -> List[Dict]
    def get_player_awards(dynasty_id, player_id) -> List[Dict]

    # Nominees
    def insert_nominee(dynasty_id, season, award_id, player_id, team_id,
                      nomination_rank, stats_snapshot, grade_snapshot)
    def get_nominees(dynasty_id, season, award_id) -> List[Dict]

    # All-Pro
    def insert_all_pro_selection(dynasty_id, season, player_id, team_id,
                                 position, team_type, vote_points, vote_share)
    def get_all_pro_teams(dynasty_id, season) -> Dict[str, List]
    def get_player_all_pro_history(dynasty_id, player_id) -> List[Dict]

    # Pro Bowl
    def insert_pro_bowl_selection(dynasty_id, season, player_id, team_id,
                                  conference, position, selection_type, combined_score)
    def get_pro_bowl_roster(dynasty_id, season, conference=None) -> Dict[str, List]
    def get_player_pro_bowl_history(dynasty_id, player_id) -> List[Dict]

    # Statistical Leaders
    def record_stat_leader(dynasty_id, season, stat_category, player_id,
                          team_id, position, stat_value, league_rank)
    def get_stat_leaders(dynasty_id, season, category=None) -> List[Dict]
    def get_player_stat_leader_history(dynasty_id, player_id) -> List[Dict]
```

#### Acceptance Criteria
- [ ] All 6 tables created with proper indexes
- [ ] award_definitions pre-populated with 8 awards
- [ ] AwardsAPI implements all 17 methods
- [ ] Dynasty isolation enforced via foreign keys
- [ ] API follows GameCycleDatabase pattern (like TeamHistoryAPI)

#### Tests
`tests/game_cycle/database/test_awards_api.py` (70+ tests)

---

### **Tollgate 2: Award Eligibility & Scoring Criteria** ✅
**Duration**: 5-6 days
**Objective**: Implement realistic scoring algorithms for each award type

#### Files to Create
- `src/game_cycle/services/awards/` (new package)
  - `__init__.py`
  - `eligibility.py` (150 lines)
  - `award_criteria.py` (600+ lines)
  - `models.py` (dataclasses)

#### Award Scoring Breakdown

**MVP Criteria** (40% stats, 40% grades, 20% team success)
```python
@dataclass
class AwardScore:
    player_id: int
    total_score: float  # 0-100
    stat_component: float  # 0-40
    grade_component: float  # 0-40
    team_success_component: float  # 0-20
    breakdown: Dict[str, Any]

class MVPCriteria:
    """
    Stats Component (0-40):
    - QB: Passing yards, TDs, passer rating, EPA
    - RB: Total yards (rush + receiving), TDs
    - WR/TE: Receiving yards, TDs, catch rate
    - Defense: Sacks, TFLs, QB hits, forced turnovers

    Grade Component (0-40):
    - Season overall grade (0-100) * 0.4

    Team Success Component (0-20):
    - Win%: 0-10 points (linear scale)
    - Playoff seed: 0-5 points (#1 seed = 5, #7 = 1, miss = 0)
    - Division title: +3 points
    - Conference championship: +2 points

    Position Weights (QB favoritism):
    - QB: 1.0x (baseline)
    - RB: 0.9x
    - WR/TE: 0.85x
    - Defense: 0.75x (rare for MVP)
    """
```

**OPOY/DPOY Criteria** (50% stats, 50% grades)
- No team success component
- Pure performance-based
- Position-neutral weighting within offense/defense

**OROY/DROY Criteria** (same as OPOY/DPOY but rookies only)
- Filter: `years_pro == 0`
- Same scoring methodology as OPOY/DPOY

**Comeback Player of the Year** (narrative-driven)
```python
def calculate_cpoy_score(player_id, season):
    """
    Comeback scenarios:
    1. Injury comeback: Missed 8+ games previous year, full season this year
    2. Performance comeback: Grade improved 15+ points from previous year
    3. New team success: Left bad team, excelled elsewhere

    Scoring:
    - 40% year-over-year improvement (grade delta)
    - 30% current season grade
    - 20% games missed previous year
    - 10% narrative strength (injury severity, age, position change)
    """
```

**All-Pro Criteria** (position rankings)
```python
def calculate_all_pro_scores(position: str, season: int):
    """
    Combined ranking system:
    - 50% season overall grade
    - 30% position-specific grade
    - 20% statistical performance vs position average

    Positions: QB(1), RB(2), FB(1), WR(2), TE(1), OL(5),
               DL(4), LB(3), CB(2), S(2), K(1), P(1), ST(1)

    Selection: Top 2N candidates per position (N = slots)
    """
```

#### Eligibility Rules
```python
class EligibilityChecker:
    MINIMUM_GAMES = 12  # 67% of 18 games
    MINIMUM_SNAP_PERCENTAGE = 0.50  # 50% of team snaps

    def is_eligible(self, player_id: int, season: int) -> bool:
        """
        Check:
        1. Played 12+ games
        2. Played 50%+ of team's offensive/defensive snaps
        3. Not on IR for entire season
        """
```

#### Acceptance Criteria
- [ ] Eligibility enforces 12-game minimum and 50% snap threshold
- [ ] MVP scoring implemented for QB, RB, WR, DE positions
- [ ] OPOY/DPOY scoring for all offensive/defensive positions
- [ ] Rookie detection via `years_pro` field
- [ ] Comeback detection via injury history or grade comparison
- [ ] All-Pro: position-based rankings with proper weighting
- [ ] Position weights applied correctly (QB favoritism for MVP)

#### Tests
- `tests/game_cycle/services/awards/test_eligibility.py` (25 tests)
- `tests/game_cycle/services/awards/test_award_criteria.py` (50 tests)

---

### **Tollgate 3: Voting Simulation Engine** ✅
**Duration**: 4-5 days
**Objective**: Simulate 50 media voters with realistic variance

#### Files to Create
- `src/game_cycle/services/awards/voting_engine.py` (400 lines)
- `src/game_cycle/services/awards/voter_archetypes.py` (200 lines)

#### Voter Archetypes (5 types)
```python
class VoterArchetype(Enum):
    BALANCED = "balanced"          # 40% (20 voters)
    STATS_FOCUSED = "stats"        # 20% (10 voters)
    ANALYTICS = "analytics"        # 20% (10 voters)
    NARRATIVE_DRIVEN = "narrative" # 10% (5 voters)
    TRADITIONAL = "traditional"    # 10% (5 voters)

@dataclass
class VoterProfile:
    voter_id: str
    archetype: VoterArchetype
    position_bias: Dict[str, float]  # {'QB': 1.2, 'RB': 1.0, 'WR': 0.8}
    variance: float  # 0.05-0.15 (5-15% score randomness)

    def adjust_score(self, score: AwardScore) -> float:
        """
        Apply archetype-specific weighting:
        - BALANCED: No adjustment (equal weight to stats/grades/team)
        - STATS_FOCUSED: 60% stats, 30% grades, 10% team
        - ANALYTICS: 20% stats, 70% grades, 10% team
        - NARRATIVE_DRIVEN: 30% stats, 30% grades, 40% team/story
        - TRADITIONAL: +20% QB bias, -10% WR/DE

        Add variance: score * (1.0 + random(-variance, +variance))
        """
```

#### Voting System (10-5-3-2-1 point allocation)
```python
class VotingEngine:
    def __init__(self, num_voters: int = 50, seed: Optional[int] = None):
        self.voters = self._generate_voters(num_voters)
        self.rng = random.Random(seed)

    def conduct_voting(
        self,
        award_id: str,
        candidates: List[AwardScore],
        season: int
    ) -> List[VotingResult]:
        """
        50 voters each pick top 5:
        1st: 10 points
        2nd: 5 points
        3rd: 3 points
        4th: 2 points
        5th: 1 point

        Max possible points: 50 voters × 10 points = 500
        Typical winner: 350-450 points (70-90% vote share)
        Landslide: 450+ points (90%+)
        Contested: 250-350 points (50-70%)

        Returns:
        - Sorted by total vote points (descending)
        - Vote share = points / 500
        - Includes all candidates with 1+ vote
        """
```

#### Tiebreaker Logic
```python
def _resolve_tie(self, tied_candidates: List[VotingResult]) -> List[VotingResult]:
    """
    If multiple candidates have same vote points:
    1. Count first-place votes
    2. Count second-place votes
    3. Higher raw score (pre-voting)
    4. Random (very rare)
    """
```

#### Acceptance Criteria
- [ ] 50 voters generated with archetype distribution (20/10/10/5/5)
- [ ] 10-5-3-2-1 point system implemented correctly
- [ ] Position bias creates realistic QB favoritism for MVP
- [ ] Variance creates realistic spread (not unanimous)
- [ ] Archetype affects score weighting (stats vs grades)
- [ ] Deterministic seed option for testing
- [ ] Tiebreaker handles edge cases (identical vote totals)

#### Tests
`tests/game_cycle/services/awards/test_voting_engine.py` (40 tests)

---

### **Tollgate 4: Awards Service Orchestration** ✅
**Duration**: 5-6 days
**Objective**: Main service that coordinates all award calculations

#### Files to Create
- `src/game_cycle/services/awards_service.py` (800+ lines)

#### Files to Modify
- `src/game_cycle/services/__init__.py` - Export AwardsService

#### Service Architecture (follow DraftService pattern)
```python
class AwardsService:
    """
    Main orchestrator for all award calculations.
    Lazy-loads all dependencies (no direct DB calls).
    Returns typed dataclasses.
    """

    def __init__(self, db_path: str, dynasty_id: str, season: int):
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season

        # Lazy-loaded (property methods)
        self._stats_api = None
        self._analytics_api = None
        self._awards_api = None
        self._team_history_api = None
        self._voting_engine = None

    # === MAJOR AWARDS ===

    def calculate_mvp(self) -> AwardResult:
        """Calculate MVP with full voting simulation."""

    def calculate_opoy(self) -> AwardResult:
        """Offensive Player of the Year (offensive positions only)."""

    def calculate_dpoy(self) -> AwardResult:
        """Defensive Player of the Year (defensive positions only)."""

    def calculate_oroy(self) -> AwardResult:
        """Offensive Rookie of the Year (years_pro == 0)."""

    def calculate_droy(self) -> AwardResult:
        """Defensive Rookie of the Year (years_pro == 0)."""

    def calculate_cpoy(self) -> AwardResult:
        """Comeback Player of the Year (injury/performance recovery)."""

    def calculate_all_awards(self) -> Dict[str, AwardResult]:
        """Calculate all 6 player awards in one call."""

    # === ALL-PRO TEAMS ===

    def select_all_pro_teams(self) -> AllProTeam:
        """Select 44 players (22 first team, 22 second team)."""

    # === PRO BOWL ===

    def select_pro_bowl_rosters(self) -> ProBowlRoster:
        """Select AFC/NFC Pro Bowl rosters."""

    # === STATISTICAL LEADERS ===

    def record_statistical_leaders(self) -> int:
        """Record top 10 in each major statistical category."""
```

#### Dataclass Models
```python
@dataclass
class AwardResult:
    award_id: str
    season: int
    winner: Dict  # {player_id, team_id, vote_points, vote_share}
    finalists: List[Dict]  # Top 5
    all_votes: List[Dict]  # All candidates with votes

@dataclass
class AllProTeam:
    season: int
    first_team: Dict[str, List[Dict]]  # {position: [players]}
    second_team: Dict[str, List[Dict]]
```

#### Acceptance Criteria
- [ ] AwardsService follows service layer pattern (no direct DB)
- [ ] Lazy-loads all dependencies (StatsAPI, AnalyticsAPI, etc.)
- [ ] calculate_all_awards() runs all 6 awards
- [ ] select_all_pro_teams() selects exactly 44 players
- [ ] record_statistical_leaders() captures 15 categories
- [ ] Returns typed dataclasses (AwardResult, AllProTeam)

#### Tests
`tests/game_cycle/services/test_awards_service.py` (60 tests)

---

### **Tollgate 5: Game Cycle Integration** ✅
**Duration**: 2-3 days
**Objective**: Trigger awards calculation automatically at season end

#### Files to Modify
- `src/game_cycle/handlers/offseason.py`
- `src/game_cycle/stage_definitions.py` (if needed)

#### Integration Logic
```python
# In OffseasonHandler

def handle_offseason_stage(self, stage: Stage) -> bool:
    """Handle offseason stages."""

    # Awards calculated at FIRST offseason stage
    if stage.stage_type == StageType.OFFSEASON_FRANCHISE_TAG:
        completed_season = stage.season_year - 1  # Just finished

        # Only calculate once per season
        if not self._awards_already_calculated(completed_season):
            self._calculate_season_awards(completed_season)

    # Continue with normal offseason processing
    # ...

def _calculate_season_awards(self, season: int) -> None:
    """Calculate and record all awards for completed season."""
    logger.info(f"🏆 Calculating awards for {season} season...")

    try:
        from ..services.awards_service import AwardsService
        awards_service = AwardsService(self._db_path, self._dynasty_id, season)

        # 1. Major awards (MVP, OPOY, DPOY, OROY, DROY, CPOY)
        results = awards_service.calculate_all_awards()

        # Log winners
        for award_id, result in results.items():
            winner = result.winner
            logger.info(
                f"  {award_id.upper()}: Player #{winner['player_id']} "
                f"({winner['vote_share']:.1%} vote share)"
            )

        # 2. All-Pro teams (44 players)
        all_pro = awards_service.select_all_pro_teams()
        logger.info(f"  All-Pro teams selected (44 players)")

        # 3. Statistical leaders (top 10 in each category)
        count = awards_service.record_statistical_leaders()
        logger.info(f"  Recorded {count} statistical leader entries")

        logger.info(f"✅ Awards calculation complete for {season}")

    except Exception as e:
        logger.error(f"❌ Failed to calculate awards: {e}")
        # Don't crash offseason - awards are non-critical
```

#### Acceptance Criteria
- [ ] Awards triggered at OFFSEASON_FRANCHISE_TAG stage
- [ ] Awards calculated for COMPLETED season (year - 1)
- [ ] Idempotent: Won't re-calculate if already exist
- [ ] Error handling: Awards failure doesn't crash offseason
- [ ] Logging: Awards results logged for debugging
- [ ] Performance: Awards calculation < 10 seconds

#### Tests
`tests/game_cycle/handlers/test_offseason_awards.py` (20 tests)

---

### **Tollgate 6: UI - Awards View** ✅
**Duration**: 5-6 days
**Objective**: Create Awards tab in main window

#### Files Created
- `game_cycle_ui/views/awards_view.py` (1400+ lines) - Complete tabbed UI with 4 tabs
  - Major Awards: 2x2 card grid layout for finalists, winner highlight
  - All-Pro: AFC/NFC tables with First Team/Second Team selections
  - Pro Bowl: AFC/NFC rosters with position groupings
  - Stat Leaders: Category-based tables with top performers

#### Files Modified
- `game_cycle_ui/main_window.py` - Added Awards tab to main navigation
- `game_cycle_ui/views/__init__.py` - Exports AwardsView

#### UI Layout (tabbed interface)
```
+---------------------------------------------------------------+
| Season: [2025 ▼]                                              |
+---------------------------------------------------------------+
| [Major Awards] [All-Pro Teams] [Pro Bowl] [Stat Leaders]     |
+---------------------------------------------------------------+
|                                                               |
| 🏆 MVP - John Smith (QB, Detroit Lions)                       |
| Vote Share: 87.3% (437 of 500 points)                        |
| Stats: 5,234 yards, 42 TDs, 8 INTs, 108.7 rating             |
| Grade: 94.2 overall                                          |
| Team: 14-4 record, #1 seed, Division Champions               |
|                                                               |
| Finalists:                                                    |
| 2. Jane Doe (RB, San Francisco 49ers) - 58.2%               |
| 3. Bob Johnson (QB, Kansas City Chiefs) - 32.4%             |
| 4. Alice Williams (WR, Miami Dolphins) - 18.6%              |
| 5. Mike Davis (DE, Dallas Cowboys) - 12.8%                  |
+---------------------------------------------------------------+
```

#### Tab Structure
- **Major Awards Tab**: All 6 awards with winners + top 5 finalists
- **All-Pro Teams Tab**: First Team (22) + Second Team (22) by position
- **Pro Bowl Tab**: AFC/NFC rosters with starters/reserves
- **Statistical Leaders Tab**: Top 10 per category with dropdown selector

#### Acceptance Criteria
- [ ] Awards view accessible from sidebar
- [ ] Season dropdown shows all seasons with awards
- [ ] Major Awards tab displays all 6 awards with finalists
- [ ] All-Pro tab shows 44 players (first + second team)
- [ ] Pro Bowl tab shows AFC/NFC rosters
- [ ] Statistical Leaders tab with category dropdown (15 categories)
- [ ] Vote share displayed as percentage
- [ ] Click player navigates to player profile
- [ ] Empty state for seasons without awards

#### Tests
`tests/game_cycle_ui/test_awards_view.py` (30 tests)

---

### **Tollgate 7: Player Profile Integration** ⬜
**Duration**: 2-3 days
**Objective**: Show player awards in career history

#### Files to Modify
- `game_cycle_ui/dialogs/player_progression_dialog.py`
- `src/game_cycle/database/progression_history_api.py`

#### Add to ProgressionHistoryAPI
```python
def get_player_accolades(self, dynasty_id: str, player_id: int) -> Dict:
    """
    Get all awards and accolades for a player.

    Returns:
        {
            'major_awards': [
                {'season': 2025, 'award': 'MVP', 'vote_share': 0.873},
                {'season': 2026, 'award': 'OPOY', 'vote_share': 0.654}
            ],
            'all_pro_selections': [
                {'season': 2025, 'team_type': 'FIRST_TEAM', 'position': 'QB'},
                {'season': 2026, 'team_type': 'FIRST_TEAM', 'position': 'QB'}
            ],
            'pro_bowl_selections': [
                {'season': 2025, 'conference': 'NFC', 'type': 'STARTER'}
            ],
            'statistical_titles': [
                {'season': 2025, 'category': 'passing_yards', 'value': 5234}
            ]
        }
    """
```

#### Player Dialog Enhancement
```
+-------------------------------+
| John Smith - QB #9            |
| Detroit Lions                 |
+-------------------------------+
| [Career Stats] [Progression]  |
+-------------------------------+
|                               |
| Awards & Honors:              |
| 🏆 2025 NFL MVP (87.3%)       |
| 🌟 3x First-Team All-Pro      |
| ⭐ 5x Pro Bowl                |
| 📊 2025 Passing Yards Leader  |
|                               |
+-------------------------------+
```

#### Acceptance Criteria
- [ ] Player progression dialog shows "Awards & Honors" section
- [ ] Major awards listed with season and vote share
- [ ] All-Pro count summarized (e.g., "3x First-Team All-Pro")
- [ ] Pro Bowl count summarized (e.g., "5x Pro Bowl")
- [ ] Statistical titles listed by season
- [ ] Empty state: "No awards yet" for players without accolades
- [ ] Awards section collapsible/expandable

#### Tests
`tests/game_cycle_ui/dialogs/test_player_progression_dialog_awards.py` (15 tests)

---

## Testing Strategy

### Unit Tests (200+ tests, 70% coverage)
1. **Database Layer** (70 tests)
   - CRUD operations for 6 tables
   - Dynasty isolation, foreign keys, unique constraints

2. **Award Criteria** (75 tests)
   - Eligibility rules (games, snaps, rookies)
   - Scoring algorithms (MVP, OPOY, DPOY, OROY, DROY, CPOY)

3. **Voting Engine** (40 tests)
   - Vote tallying, archetypes, variance
   - Position bias, score adjustments

4. **Service Layer** (60 tests)
   - End-to-end award calculations
   - Mocked dependencies, deterministic results

### Integration Tests (50+ tests, 20% coverage)
1. **Game Cycle Integration** (20 tests)
   - Awards triggered at correct stage
   - Idempotency, error handling

2. **UI Integration** (30 tests)
   - Awards display, season filtering
   - Accolades in player profile

### Edge Case Tests (30+ tests, 10% coverage)
- Multiple players with identical vote totals
- Position with no eligible players
- Season with no games played
- Missing stats for eligible player
- Player traded mid-season (team attribution)
- Rookie with years_pro incorrectly set

---

## Performance Analysis

### Expected Performance
- **Calculate all 6 major awards**: ~2-3 seconds
- **Select All-Pro teams**: ~1-2 seconds (22 positions × voting)
- **Select Pro Bowl rosters**: ~1-2 seconds
- **Record statistical leaders**: <1 second (15 categories × 10 players)
- **Total per season**: <10 seconds

### Optimizations
1. **Database Indexes**: Fast season/player lookups
2. **Lazy Loading**: Only load APIs when needed
3. **Batch Inserts**: Record all nominees in single transaction
4. **Caching**: Cache voter profiles (50 voters reused)

---

## Integration with Future Milestones

### Hall of Fame (#17)
Awards are primary HOF voting factor:
- **MVP**: +50 HOF points
- **OPOY/DPOY**: +30 HOF points
- **All-Pro First Team**: +10 points each
- **All-Pro Second Team**: +5 points each
- **Pro Bowl**: +3 points each

### Media Coverage (#13)
Award winners generate headlines:
- "Player X wins MVP with 87% of vote"
- "First [position] to win DPOY since 2018"
- "Unanimous All-Pro selection"

### Social Media (#14)
Awards drive fan engagement:
- Sentiment boost for winners (+15-20)
- Hashtag trends (#MVP, #AllPro, #ProBowl)
- Viral moments for controversial votes

### Player Popularity (#15)
Awards increase star power:
- **MVP**: +15-20 popularity
- **OPOY/DPOY**: +10-15 popularity
- **Rookie awards**: +8-12 popularity
- **All-Pro**: +5-8 popularity
- **Pro Bowl**: +3-5 popularity

---

## Future Enhancements (Post-Milestone)

### Coach of the Year (COY)
**Blocked by**: Milestone #21 (Head Coaching System)
**Logic**: Team improvement + playoff success + win% vs expectations

### Executive of the Year (EOY)
**Blocked by**: Milestone #37 (GM Behaviors)
**Logic**: Draft success + FA moves + team building + cap management

### Award Ceremony Event
**Enhancement**: Create special event during Super Bowl week
- UI dialog with winners announced
- Press conference quotes
- Social media reactions

### Historical Comparisons
**Enhancement**: Compare winners to past greats
- "Most MVPs in franchise history"
- "First player to win OPOY and DPOY"
- "Youngest MVP ever"

---

## Risks & Mitigations

### Risk 1: Advanced Analytics Dependency
**Status**: Milestone #3 marked "Not Started"
**Reality**: AnalyticsAPI already exists with full grading system
**Mitigation**: Use existing grading infrastructure
**Fallback**: Can implement stats-only scoring if grades unavailable

### Risk 2: Performance with Large Dynasties
**Concern**: 50-season dynasty with 1600+ players
**Mitigation**:
- Eligibility filters early (12-game minimum)
- Index-backed queries
- Limit candidates to top 100 per award

### Risk 3: UI Complexity
**Concern**: Awards view more complex than existing views
**Mitigation**:
- Follow existing patterns (StatsView, TradingView)
- Start with text-based display, enhance iteratively
- Separate controller logic from view

---

## Critical Files Summary

### Backend Core (Must Create)
1. `src/game_cycle/database/awards_api.py` (350 lines)
2. `src/game_cycle/services/awards/award_criteria.py` (600 lines)
3. `src/game_cycle/services/awards/voting_engine.py` (400 lines)
4. `src/game_cycle/services/awards_service.py` (800 lines)

### Database Schema (Must Modify)
5. `src/game_cycle/database/schema.sql`
6. `src/game_cycle/database/full_schema.sql`

### Integration (Must Modify)
7. `src/game_cycle/handlers/offseason.py`

### UI (Must Create)
8. `game_cycle_ui/views/awards_view.py` (600 lines)
9. `game_cycle_ui/controllers/awards_controller.py` (300 lines)

---

## Timeline Estimate

**Total Duration**: 4-6 weeks (30-40 days)

| Tollgate | Duration | Dependencies |
|----------|----------|--------------|
| 1. Database | 3-4 days | None |
| 2. Criteria | 5-6 days | Tollgate 1 |
| 3. Voting | 4-5 days | Tollgate 2 |
| 4. Service | 5-6 days | Tollgates 1-3 |
| 5. Integration | 2-3 days | Tollgate 4 |
| 6. UI | 5-6 days | Tollgate 4 |
| 7. Player Profile | 2-3 days | Tollgates 4, 6 |

**Critical Path**: Tollgates 1 → 2 → 3 → 4 → 5

**Parallel Work Possible**:
- Tollgate 6 (UI) can start after Tollgate 4 completes
- Tollgate 7 (Player Profile) can start after Tollgate 4 completes

---

## Success Criteria

### Tollgate Completion
- All 7 tollgates completed with acceptance criteria met
- 280+ tests passing (200 unit, 50 integration, 30 edge cases)
- 70%+ code coverage

### Functional Requirements
- 6 major awards calculated annually (MVP, OPOY, DPOY, OROY, DROY, CPOY)
- All-Pro teams selected (44 players)
- Pro Bowl rosters selected (AFC/NFC)
- Statistical leaders tracked (top 10 in 15 categories)
- Realistic voting simulation (50 voters, archetypes, variance)
- UI displays all awards with vote shares
- Player profiles show career accolades

### Performance Requirements
- Awards calculation < 10 seconds per season
- No impact on game cycle progression
- Database queries optimized with indexes

### Quality Requirements
- Dynasty isolation enforced
- Service layer pattern followed
- Error handling prevents offseason crashes
- Logging for debugging

---

## Conclusion

The Awards System is **ready for immediate implementation**. All infrastructure dependencies are complete (StatsAPI, AnalyticsAPI, TeamHistoryAPI), and the existing grading system provides the foundation for realistic award voting.

This milestone will add significant depth to the dynasty experience by:
- Recognizing exceptional player performance
- Creating historical records and legacy
- Driving player popularity and fan engagement
- Laying groundwork for Hall of Fame (#17)

**Recommended Start**: Begin with Tollgate 1 (Database Foundation) immediately.
