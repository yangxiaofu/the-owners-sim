# Milestone: Player Retirements

> **Status:** ✅ Complete (All Tollgates Finished)
> **Dependencies:** Statistics (done), Progression (done), Awards (done)

## Overview

Players make retirement decisions based on age, performance decline, injuries, and career accomplishments. Retirements create emotional moments, roster turnover, and feed into the Hall of Fame pipeline.

## Design Philosophy

- **Retirement = End of Career** — Players who retire are removed from active rosters and cannot be re-signed
- **Multiple Triggers** — Age/decline, injuries, championship, contract disputes, personal reasons
- **Career Summary** — Every retirement generates a career recap for legacy tracking
- **Integrated UI** — Retirements displayed in OFFSEASON_HONORS stage alongside awards and Super Bowl results

## UI Approach: OFFSEASON_HONORS Redesign

The existing OFFSEASON_HONORS stage will be transformed into a **Season Recap** page with three tabs:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  SEASON RECAP - 2025                                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  [ Super Bowl ]  [ Awards ]  [ Retirements ]                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  (Tab content area)                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Tab 1: Super Bowl
- Champion team with logo and confetti styling
- Final score and game summary
- Super Bowl MVP with stats
- Link to box score

### Tab 2: Awards
- MVP, OPOY, DPOY, OROY, DROY, CPOY
- All-Pro First Team and Second Team
- Pro Bowl rosters (AFC/NFC)
- Statistical leaders

### Tab 3: Retirements
- List of retiring players with career summaries
- Filter by: Your Team / League-wide
- Click for detailed career stats
- Notable retirements highlighted (Pro Bowlers, champions)

---

## Status

| Tollgate | Description | Status |
|----------|-------------|--------|
| 1 | Database Schema | ✅ Complete |
| 2 | Retirement Decision Engine | ✅ Complete |
| 3 | Career Summary Generator | ✅ Complete |
| 4 | Retirement Service Integration | ✅ Complete |
| 5 | UI - Season Recap View | ✅ Complete |
| 6 | UI - Retirement Details | ✅ Complete |
| 7 | Integration Testing | ✅ Complete |

---

## Tollgate 1: Database Schema

**Goal**: Add tables to track retirements and career summaries

### Deliverables

- [x] Add `retired_players` table to schema
- [x] Add `career_summaries` table to schema
- [x] Create `RetiredPlayersAPI` class
- [x] Write unit tests (18 tests passing)

### Schema - retired_players

```sql
CREATE TABLE IF NOT EXISTS retired_players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    player_id INTEGER NOT NULL,
    retirement_season INTEGER NOT NULL,
    retirement_reason TEXT NOT NULL CHECK(retirement_reason IN (
        'age_decline',      -- Age + performance below threshold
        'injury',           -- Career-ending or chronic injury
        'championship',     -- Retired after winning Super Bowl
        'contract',         -- Refused paycut, chose retirement
        'personal',         -- Family reasons, other interests
        'released'          -- Cut and chose not to continue
    )),
    final_team_id INTEGER NOT NULL,
    years_played INTEGER NOT NULL,
    age_at_retirement INTEGER NOT NULL,
    announced_date TEXT,  -- In-game date of announcement
    one_day_contract_team_id INTEGER,  -- Team for ceremonial signing
    hall_of_fame_eligible_season INTEGER,  -- Season when HOF eligible (retirement + 5)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(dynasty_id, player_id)
);

CREATE INDEX idx_retired_players_dynasty_season
ON retired_players(dynasty_id, retirement_season);
```

### Schema - career_summaries

```sql
CREATE TABLE IF NOT EXISTS career_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    player_id INTEGER NOT NULL,
    -- Basic info
    full_name TEXT NOT NULL,
    position TEXT NOT NULL,
    draft_year INTEGER,
    draft_round INTEGER,
    draft_pick INTEGER,
    -- Career totals (position-specific fields populated)
    games_played INTEGER DEFAULT 0,
    games_started INTEGER DEFAULT 0,
    -- Passing
    pass_yards INTEGER DEFAULT 0,
    pass_tds INTEGER DEFAULT 0,
    pass_ints INTEGER DEFAULT 0,
    -- Rushing
    rush_yards INTEGER DEFAULT 0,
    rush_tds INTEGER DEFAULT 0,
    -- Receiving
    receptions INTEGER DEFAULT 0,
    rec_yards INTEGER DEFAULT 0,
    rec_tds INTEGER DEFAULT 0,
    -- Defense
    tackles INTEGER DEFAULT 0,
    sacks REAL DEFAULT 0,
    interceptions INTEGER DEFAULT 0,
    forced_fumbles INTEGER DEFAULT 0,
    -- Kicking
    fg_made INTEGER DEFAULT 0,
    fg_attempted INTEGER DEFAULT 0,
    -- Accomplishments
    pro_bowls INTEGER DEFAULT 0,
    all_pro_first_team INTEGER DEFAULT 0,
    all_pro_second_team INTEGER DEFAULT 0,
    mvp_awards INTEGER DEFAULT 0,
    super_bowl_wins INTEGER DEFAULT 0,
    super_bowl_mvps INTEGER DEFAULT 0,
    -- Teams
    teams_played_for TEXT,  -- JSON array of team_ids
    primary_team_id INTEGER,  -- Team with most seasons
    -- Calculated
    career_approximate_value INTEGER DEFAULT 0,  -- WAR-like metric
    hall_of_fame_score INTEGER DEFAULT 0,  -- Likelihood score 0-100
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(dynasty_id, player_id)
);
```

---

## Tollgate 2: Retirement Decision Engine

**Goal**: Create logic to determine when players should retire

**File**: `src/game_cycle/services/retirement_decision_engine.py`

### Deliverables

- [x] Create `RetirementDecisionEngine` class
- [x] Implement age-based retirement probability
- [x] Implement performance decline detection
- [x] Implement injury-based retirement
- [x] Implement championship retirement (ring chaser fulfilled)
- [x] Implement contract-based retirement
- [x] Write unit tests (35 tests passing)

### Retirement Probability by Position

| Position | Base Retirement Age | Decline Threshold | Max Age |
|----------|---------------------|-------------------|---------|
| QB       | 38                  | OVR < 70          | 45      |
| RB       | 30                  | OVR < 65          | 34      |
| FB       | 32                  | OVR < 60          | 36      |
| WR       | 33                  | OVR < 65          | 38      |
| TE       | 33                  | OVR < 65          | 38      |
| OL       | 34                  | OVR < 65          | 40      |
| DL       | 32                  | OVR < 65          | 38      |
| EDGE     | 32                  | OVR < 65          | 36      |
| LB       | 32                  | OVR < 65          | 36      |
| CB       | 32                  | OVR < 65          | 36      |
| S        | 33                  | OVR < 65          | 38      |
| K        | 40                  | OVR < 70          | 48      |
| P        | 38                  | OVR < 70          | 45      |

### Retirement Decision Logic

```python
def calculate_retirement_probability(player, context) -> tuple[float, str]:
    """
    Returns (probability 0.0-1.0, reason_if_retiring)

    Factors:
    1. Age vs position baseline
    2. Performance decline (OVR drop year-over-year)
    3. Injury history (season-ending injuries)
    4. Championship status (just won Super Bowl)
    5. Contract status (released, no offers)
    6. Career accomplishments (nothing left to prove)
    """

    probability = 0.0
    reason = None

    # Age factor (primary driver)
    years_past_base = player.age - POSITION_RETIREMENT_AGES[player.position]
    if years_past_base >= 0:
        probability += 0.15 * (years_past_base + 1)  # 15% per year past base

    # Performance decline
    if player.ovr < POSITION_DECLINE_THRESHOLDS[player.position]:
        probability += 0.25
        reason = 'age_decline'

    # Injury history
    if player.career_ending_injury:
        return (0.95, 'injury')
    if player.seasons_missed_to_injury >= 2:
        probability += 0.20

    # Championship retirement (ring chaser satisfied)
    if context.just_won_super_bowl and player.age >= 33:
        if player.super_bowl_wins == 1:  # First ring
            probability += 0.30
            reason = 'championship'

    # Contract/released
    if context.released_and_unsigned:
        probability += 0.40
        reason = 'released'

    # Career accomplishments (veterans with nothing to prove)
    if player.mvp_awards >= 1 and player.super_bowl_wins >= 1 and player.age >= 35:
        probability += 0.25

    # Random personal factor
    if player.age >= 30:
        probability += random.uniform(0, 0.05)

    return (min(probability, 0.95), reason or 'age_decline')
```

### Retirement Timing

- **Post-Super Bowl retirements**: Champions and veterans (OFFSEASON_HONORS)
- **Post-release retirements**: Cut players who don't get signed
- **Mid-season retirement**: Rare, injury-based only

---

## Tollgate 3: Career Summary Generator

**Goal**: Generate comprehensive career summaries for retiring players

**File**: `src/game_cycle/services/career_summary_generator.py`

### Deliverables

- [x] Create `CareerSummaryGenerator` class
- [x] Aggregate career statistics from player_game_stats
- [x] Calculate career accomplishments (awards, Pro Bowls, etc.)
- [x] Calculate Hall of Fame score
- [x] Generate narrative summary text
- [x] Write unit tests (29 tests passing)

### Hall of Fame Score Calculation

```python
def calculate_hof_score(summary: CareerSummary) -> int:
    """
    Returns 0-100 score indicating HOF likelihood.

    Factors weighted by importance:
    - MVP awards: +25 per award (max +50)
    - Super Bowl wins: +15 per win (max +30)
    - All-Pro First Team: +8 per selection
    - All-Pro Second Team: +4 per selection
    - Pro Bowls: +2 per selection (max +20)
    - Career stats vs. position thresholds: +0-20
    - Longevity (10+ seasons): +5-10
    """
    score = 0

    # MVP awards (max +50)
    score += min(summary.mvp_awards * 25, 50)

    # Super Bowl wins (max +30)
    score += min(summary.super_bowl_wins * 15, 30)

    # All-Pro selections
    score += summary.all_pro_first_team * 8
    score += summary.all_pro_second_team * 4

    # Pro Bowls (max +20)
    score += min(summary.pro_bowls * 2, 20)

    # Position-specific career stats bonus
    score += _calculate_stats_bonus(summary)  # 0-20

    # Longevity bonus
    if summary.years_played >= 15:
        score += 10
    elif summary.years_played >= 10:
        score += 5

    return min(score, 100)
```

### Narrative Summary Template

```
{full_name} retires after {years_played} seasons in the league.

{position_specific_career_highlights}

Career Highlights:
• {games_played} games played ({games_started} starts)
• {primary_stat_line}
• {awards_summary}
• {teams_summary}

{hof_projection_if_applicable}
```

---

## Tollgate 4: Retirement Service Integration

**Goal**: Integrate retirement logic into game cycle

**File**: `src/game_cycle/services/retirement_service.py`

### Deliverables

- [x] Create `RetirementService` class
- [x] Integrate with OFFSEASON_HONORS stage handler
- [x] Process post-Super Bowl retirements
- [x] Process post-release retirements (during FA/cuts)
- [x] Handle one-day contract ceremonies
- [x] Remove retired players from active rosters
- [x] Write unit tests (28 tests passing)

### Service Interface

```python
class RetirementService:
    def __init__(self, db_path: str, dynasty_id: str, season: int):
        ...

    def process_post_season_retirements(
        self,
        super_bowl_winner_id: Optional[int] = None
    ) -> List[RetirementResult]:
        """
        Evaluate all players for retirement after season ends.
        Called during OFFSEASON_HONORS stage.
        """

    def process_player_retirement(
        self,
        player_id: int,
        reason: str
    ) -> RetirementResult:
        """Process single player retirement with career summary generation."""

    def get_season_retirements(self) -> List[RetiredPlayer]:
        """Get all retirements for current season."""

    def get_player_career_summary(self, player_id: int) -> CareerSummary:
        """Get career summary for a retired player."""

    def process_one_day_contract(
        self,
        player_id: int,
        team_id: int
    ) -> bool:
        """Process ceremonial one-day contract signing."""
```

### RetirementResult Dataclass

```python
@dataclass
class RetirementResult:
    player_id: int
    player_name: str
    position: str
    age: int
    reason: str
    years_played: int
    final_team_id: int
    career_summary: CareerSummary
    is_notable: bool  # Pro Bowler, champion, etc.
    headline: str  # Generated headline for media
```

---

## Tollgate 5: UI - Season Recap View

**Goal**: Transform OFFSEASON_HONORS into tabbed Season Recap view

**File**: `game_cycle_ui/views/season_recap_view.py` (rename from honors_view.py)

### Deliverables

- [x] Create `SeasonRecapView` with tabbed interface
- [x] Implement Super Bowl tab with champion display (SuperBowlResultWidget)
- [x] Implement Awards tab with all award categories (embedded AwardsView)
- [x] Implement Retirements tab with player list (RetirementCardWidget, table)
- [x] Add filtering (Your Team / Notable Only / All)
- [x] Update main_window.py to use SeasonRecapView
- [x] Write UI tests (22 tests passing)

### UI Layout - Super Bowl Tab

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SUPER BOWL LIX                                     │
│                                                                             │
│                    ┌─────────────────────────────┐                          │
│                    │      🏆 CHAMPIONS 🏆        │                          │
│                    │                             │                          │
│                    │    KANSAS CITY CHIEFS       │                          │
│                    │           38 - 24           │                          │
│                    │    vs Philadelphia Eagles   │                          │
│                    │                             │                          │
│                    └─────────────────────────────┘                          │
│                                                                             │
│  SUPER BOWL MVP                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  QB Patrick Mahomes                                                   │  │
│  │  28/35, 327 YDS, 3 TD, 0 INT | 134.2 RTG                             │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│                            [View Box Score]                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

### UI Layout - Retirements Tab

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  RETIREMENTS - 2025 SEASON                    [Your Team ▼] [Notable Only] │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  NOTABLE RETIREMENTS                                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  ⭐ QB Aaron Rodgers (42) - New York Jets                            │  │
│  │     19 seasons | 4x MVP | 1x Super Bowl Champion                     │  │
│  │     65,432 Pass Yds | 489 TDs | Hall of Fame Score: 94               │  │
│  │                                                           [Details]   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  ⭐ WR Davante Adams (33) - Las Vegas Raiders                        │  │
│  │     12 seasons | 5x Pro Bowl | 2x All-Pro                            │  │
│  │     11,234 Rec Yds | 89 TDs | Hall of Fame Score: 62                 │  │
│  │                                                           [Details]   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  OTHER RETIREMENTS (24 players)                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Player              | Pos | Age | Team          | Seasons | Reason   │  │
│  │  ─────────────────────────────────────────────────────────────────── │  │
│  │  John Smith          | LB  | 34  | DAL Cowboys   | 11      | Decline  │  │
│  │  Mike Johnson        | RB  | 31  | CHI Bears     | 8       | Injury   │  │
│  │  ...                                                                  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  Total Retirements: 26 players                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tollgate 6: UI - Retirement Details Dialog

**Goal**: Create detailed view for individual player career summary

**File**: `game_cycle_ui/dialogs/retirement_detail_dialog.py`

### Deliverables

- [x] Create `RetirementDetailDialog` class
- [x] Display full career statistics (position-specific)
- [x] Show career timeline (teams played for)
- [x] Display awards and accomplishments
- [x] Show Hall of Fame projection with progress bar
- [x] Add "Offer One-Day Contract" button (for your team's former players)
- [x] Connect dialog to SeasonRecapView (click handling)
- [x] Write unit tests (14 tests passing)

### UI Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  CAREER RETROSPECTIVE                                              [X]     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────┐   QB AARON RODGERS                                         │
│  │            │   Age 42 | 19 Seasons | HOF Score: 94                       │
│  │   [Photo]  │                                                             │
│  │            │   "One of the greatest quarterbacks to ever play the game"  │
│  └────────────┘                                                             │
│                                                                             │
│  CAREER STATISTICS                                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Games: 291 (287 starts)                                              │  │
│  │  Passing: 65,432 yds | 489 TD | 112 INT | 103.6 RTG                   │  │
│  │  Rushing: 3,845 yds | 37 TD                                           │  │
│  │  Passer Rating: 103.6 (5th all-time)                                  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  CAREER TIMELINE                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  2005-2007  Green Bay Packers (Backup)                                │  │
│  │  2008-2022  Green Bay Packers (Starter) ⭐                            │  │
│  │  2023-2025  New York Jets                                             │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ACCOMPLISHMENTS                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  🏆 1x Super Bowl Champion (XLV)                                      │  │
│  │  🏅 4x NFL MVP (2011, 2014, 2020, 2021)                               │  │
│  │  ⭐ 10x Pro Bowl                                                       │  │
│  │  🥇 4x First-Team All-Pro                                             │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  HALL OF FAME PROJECTION                                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Score: 94/100 - FIRST BALLOT LOCK                                    │  │
│  │  ████████████████████████████████████████████████░░░░░░              │  │
│  │  Eligible: 2030 Season                                                │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│         [Offer One-Day Contract]                           [Close]         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tollgate 7: Integration Testing

**Goal**: End-to-end testing of retirement system

### Deliverables

- [x] Create integration test file (`tests/test_game_cycle/integration/test_retirement_integration.py`)
- [x] All 14 integration tests passing

### Test Coverage (14 tests)

| Test Class | Test Name | Status |
|------------|-----------|--------|
| TestChampionRetirement | test_veteran_retires_after_super_bowl_win | ✅ |
| TestAgeBasedRetirement | test_rb_retires_at_position_threshold | ✅ |
| TestAgeBasedRetirement | test_young_player_does_not_retire | ✅ |
| TestPerformanceDeclineRetirement | test_severely_declining_player_retires | ✅ |
| TestCareerSummaryAccuracy | test_career_summary_aggregates_stats | ✅ |
| TestHallOfFameScore | test_hof_score_first_ballot_candidate | ✅ |
| TestHallOfFameScore | test_hof_score_average_career | ✅ |
| TestOneDayContract | test_one_day_contract_updates_database | ✅ |
| TestMultipleRetirements | test_multiple_retirements_processed | ✅ |
| TestMultipleRetirements | test_retirements_categorized_correctly | ✅ |
| TestRetirementPersistence | test_retirement_saved_to_database | ✅ |
| TestRetirementPersistence | test_career_summary_saved_to_database | ✅ |
| TestIdempotency | test_second_run_does_not_duplicate | ✅ |
| TestUserTeamFilter | test_user_team_retirements_tracked | ✅ |

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/game_cycle/database/schema.sql` | Add retired_players, career_summaries tables |
| `src/game_cycle/handlers/offseason.py` | Integrate retirement processing in HONORS stage |
| `game_cycle_ui/views/offseason_view.py` | Route to SeasonRecapView for HONORS |
| `game_cycle_ui/controllers/stage_controller.py` | Handle retirement stage logic |

## Files to Create

| File | Purpose |
|------|---------|
| `src/game_cycle/database/retired_players_api.py` | Database API for retirements |
| `src/game_cycle/services/retirement_decision_engine.py` | Retirement probability logic |
| `src/game_cycle/services/career_summary_generator.py` | Career stats aggregation |
| `src/game_cycle/services/retirement_service.py` | Main retirement service |
| `game_cycle_ui/views/season_recap_view.py` | Tabbed Season Recap UI |
| `game_cycle_ui/dialogs/retirement_detail_dialog.py` | Career summary dialog |
| `tests/test_game_cycle/services/test_retirement_service.py` | Service tests |
| `tests/test_game_cycle/services/test_retirement_decision_engine.py` | Engine tests |
| `tests/test_game_cycle/integration/test_retirement_integration.py` | E2E tests |

---

## Implementation Order

1. **T1: Database Schema** - Foundation for storing retirement data
2. **T2: Decision Engine** - Core logic for who retires
3. **T3: Career Summary** - Generate the retrospective data
4. **T4: Service Integration** - Wire into game cycle
5. **T5: Season Recap UI** - Transform OFFSEASON_HONORS
6. **T6: Detail Dialog** - Career retrospective view
7. **T7: Integration Tests** - End-to-end validation

---

## Out of Scope (Future)

- Hall of Fame voting system (separate milestone #18)
- Mid-season retirements (rare edge case)
- Retirement press conferences (media milestone)
- Jersey retirement ceremonies (team history milestone)
- "Un-retirement" (player comes back)