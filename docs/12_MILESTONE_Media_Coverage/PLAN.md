# Milestone 12: Media Coverage

## Executive Summary

The Media Coverage milestone adds a narrative layer to the simulation, transforming raw statistics and events into engaging sports journalism content. This creates the illusion of a living NFL world with power rankings, headlines, award race coverage, trade rumors, and press conferences.

**Core Vision**: Make the simulation feel alive through generated narratives that react to game outcomes, player performances, transactions, and season storylines.

---

## Milestone Placement

Based on the existing milestone structure and dependencies:

- **Recommended Number**: `12_MILESTONE_Media_Coverage/`
- **Dependencies**: Milestones 1-11 (especially 4: Statistics, 8: Team Statistics, 10: Awards System)
- **Phase**: Post-foundation, enhancement layer

---

## Tollgate Overview

| Tollgate | Name | Status | Dependencies |
|----------|------|--------|--------------|
| 1 | Database Foundation | ✅ COMPLETE | None |
| 2 | Power Rankings System | ✅ COMPLETE | Tollgate 1 |
| 3 | Headline Generation Engine | ✅ COMPLETE | Tollgate 1 |
| 4 | Game Recap Narratives | ✅ COMPLETE | Tollgate 3 |
| 5 | Award Race Coverage | ✅ COMPLETE | Tollgate 3, Awards System |
| 6 | Rumor Mill & Speculation | ⏭️ SKIPPED | Tollgate 3 |
| 7 | UI Integration | ✅ COMPLETE | Tollgates 2-5 |

**Status**: Milestone effectively complete (Tollgate 6 skipped - can be added later)

---

## Dependency Flow

```
Tollgate 1: Database Foundation
    │
    ├──► Tollgate 2: Power Rankings ──────────┐
    │                                         │
    ├──► Tollgate 3: Headline Engine ─────────┤
    │         │                               │
    │         ├──► Tollgate 4: Game Recaps ───┤
    │         │                               ├──► Tollgate 7: UI Integration
    │         ├──► Tollgate 5: Award Coverage─┤
    │         │                               │
    │         └──► Tollgate 6: Rumor Mill ────┘
    │
    └── (External: Awards System Milestone 10)
```

---

## Tollgate Details

### Tollgate 1: Database Foundation ✅ COMPLETE
**Duration**: 2 days
**Goal**: Create database schema for persisting media coverage content

**New Tables**:

```sql
-- Power rankings history
CREATE TABLE power_rankings (
    id INTEGER PRIMARY KEY,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    rank INTEGER NOT NULL,
    previous_rank INTEGER,
    tier TEXT NOT NULL,  -- 'ELITE', 'CONTENDER', 'PLAYOFF', 'BUBBLE', 'REBUILDING'
    blurb TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(dynasty_id, season, week, team_id)
);

-- Headlines and stories
CREATE TABLE media_headlines (
    id INTEGER PRIMARY KEY,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,
    headline_type TEXT NOT NULL,  -- 'GAME_RECAP', 'TRADE', 'INJURY', 'AWARD', 'RUMOR', 'POWER_RANKING'
    headline TEXT NOT NULL,
    subheadline TEXT,
    body_text TEXT,
    sentiment TEXT,  -- 'POSITIVE', 'NEGATIVE', 'NEUTRAL', 'HYPE', 'CRITICAL'
    priority INTEGER DEFAULT 50,  -- 1-100 for sorting
    team_ids TEXT,  -- JSON array of related team IDs
    player_ids TEXT,  -- JSON array of related player IDs
    metadata TEXT,  -- JSON for type-specific data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Narrative arcs (multi-week storylines)
CREATE TABLE narrative_arcs (
    id INTEGER PRIMARY KEY,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    arc_type TEXT NOT NULL,  -- 'MVP_RACE', 'PLAYOFF_PUSH', 'HOT_SEAT', 'DYNASTY', 'RIVALRY', 'COMEBACK'
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'ACTIVE',  -- 'ACTIVE', 'RESOLVED', 'ABANDONED'
    start_week INTEGER NOT NULL,
    end_week INTEGER,
    team_id INTEGER,
    player_id INTEGER,
    metadata TEXT,  -- JSON for arc-specific data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Press quotes (coach/player quotes)
CREATE TABLE press_quotes (
    id INTEGER PRIMARY KEY,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,
    quote_type TEXT NOT NULL,  -- 'POSTGAME', 'PRESSER', 'REACTION', 'PREDICTION'
    speaker_type TEXT NOT NULL,  -- 'COACH', 'PLAYER', 'GM', 'ANALYST'
    speaker_id INTEGER,  -- player_id or NULL for coaches/analysts
    team_id INTEGER,
    quote_text TEXT NOT NULL,
    context TEXT,  -- What prompted this quote
    sentiment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**New API Class**: `src/game_cycle/database/media_coverage_api.py`

**Methods**:
- `save_power_rankings(dynasty_id, season, week, rankings: List[Dict])`
- `get_power_rankings(dynasty_id, season, week) -> List[Dict]`
- `get_ranking_history(dynasty_id, season, team_id) -> List[Dict]`
- `save_headline(dynasty_id, season, week, headline_data: Dict)`
- `get_headlines(dynasty_id, season, week, headline_type=None) -> List[Dict]`
- `get_top_headlines(dynasty_id, season, week, limit=10) -> List[Dict]`
- `save_narrative_arc(dynasty_id, arc_data: Dict)`
- `get_active_arcs(dynasty_id, season) -> List[Dict]`
- `update_arc_status(arc_id, status, end_week=None)`
- `save_quote(dynasty_id, season, week, quote_data: Dict)`
- `get_quotes(dynasty_id, season, week, quote_type=None) -> List[Dict]`

**Acceptance Criteria**:
- [x] All 4 tables created in `full_schema.sql`
- [x] MediaCoverageAPI class with all methods (11 public methods + 4 converters)
- [x] Unit tests for CRUD operations (23 tests passing - exceeded target of 15!)
- [x] Dynasty isolation verified for all queries (2 dedicated isolation tests)

**Files Created**:
- `src/game_cycle/database/full_schema.sql` - Added 4 new tables + 16 indexes
- `src/game_cycle/database/media_coverage_api.py` - Complete API with 4 dataclasses
- `tests/game_cycle/database/test_media_coverage_api.py` - 23 comprehensive tests

---

### Tollgate 2: Power Rankings System ✅ COMPLETE
**Duration**: 3 days
**Goal**: Generate weekly power rankings based on team performance

**New Service**: `src/game_cycle/services/power_rankings_service.py`

**Ranking Algorithm Factors**:
| Factor | Weight | Data Source |
|--------|--------|-------------|
| Win-Loss Record | 30% | StandingsAPI |
| Point Differential | 20% | StandingsAPI |
| Recent Performance (L4) | 20% | BoxScoresAPI |
| Strength of Victory | 15% | Schedule + Standings |
| Quality Wins | 10% | HeadToHeadAPI |
| Injuries Impact | 5% | InjuryService |

**Tier Classification**:
- **ELITE** (Ranks 1-4): Championship favorites
- **CONTENDER** (Ranks 5-10): Playoff locks, Super Bowl hopefuls
- **PLAYOFF** (Ranks 11-16): Wild card contenders
- **BUBBLE** (Ranks 17-22): On the fringe
- **REBUILDING** (Ranks 23-32): Looking to next year

**Blurb Generation Templates**:
```python
TIER_TEMPLATES = {
    "ELITE": [
        "{team} continues to dominate, looking like the team to beat.",
        "No one wants to face {team} in January.",
        "{team}'s offense/defense is simply unstoppable right now."
    ],
    "REBUILDING": [
        "{team} is playing for draft position at this point.",
        "The future is the focus in {city}.",
        "A long offseason awaits {team}."
    ]
}
```

**Methods**:
- `calculate_rankings(dynasty_id, season, week) -> List[PowerRanking]`
- `generate_blurb(team_id, rank, tier, stats) -> str`
- `get_movement(current_rank, previous_rank) -> str`  # "▲3", "▼2", "—"

**Acceptance Criteria**:
- [x] Rankings calculated using weighted algorithm
- [x] Tier assignment logic working correctly
- [x] Blurb generation with variety (100+ templates across tiers)
- [x] Week-over-week movement tracking
- [x] Unit tests (45 tests passing)
- [x] Adaptive weights for early season (Weeks 1-3)

**Implementation Details**:
- `src/game_cycle/services/power_rankings_service.py` - Main service (700+ lines)
- `tests/game_cycle/services/test_power_rankings_service.py` - Comprehensive test suite (45 tests)

---

### Tollgate 3: Headline Generation Engine ✅ COMPLETE
**Duration**: 4 days
**Goal**: Create event-driven headline generation system

**New Service**: `src/game_cycle/services/headline_generator.py`

**Architecture**:
```
Game/Event Occurs
      │
      ▼
HeadlineGenerator.generate(event_type, event_data)
      │
      ├── _analyze_significance(event_data) -> priority
      │
      ├── _select_template(event_type, significance)
      │
      ├── _fill_template(template, event_data) -> headline
      │
      ├── _generate_subheadline(headline, event_data)
      │
      └── _determine_sentiment(event_data) -> sentiment
```

**Headline Types & Triggers**:

| Type | Trigger | Example Headlines |
|------|---------|-------------------|
| GAME_RECAP | Game completion | "{winner} Dominates {loser} {score}" |
| BLOWOUT | 21+ point margin | "{winner} Embarrasses {loser} in {score} Rout" |
| UPSET | Lower seed wins | "Stunning Upset: {underdog} Takes Down {favorite}" |
| COMEBACK | 14+ point comeback | "{team} Mounts Incredible {points}-Point Comeback" |
| INJURY | Star player injury | "{player} Suffers {injury}, Out {duration}" |
| MILESTONE | Record achieved | "{player} Joins Elite Company with {milestone}" |
| TRADE | Trade completed | "Blockbuster: {team1} Acquires {player} from {team2}" |
| SIGNING | FA signing | "{player} Signs {years}-Year, ${value}M Deal with {team}" |
| AWARD | Weekly/season award | "{player} Named {award} After {stat} Performance" |
| RUMOR | Trade/FA speculation | "Sources: {team} Showing Interest in {player}" |

**Template System**:
```python
class HeadlineTemplate:
    """Template with placeholders and conditions."""
    template: str  # "{team} {verb} {opponent} in {adjective} {margin} Victory"
    conditions: Dict[str, Any]  # {"margin": ">14", "home_team": True}
    sentiment: str
    priority_boost: int  # Added to base priority

GAME_RECAP_TEMPLATES = [
    HeadlineTemplate(
        template="{winner} Cruises Past {loser}, {score}",
        conditions={"margin": ">=14"},
        sentiment="POSITIVE",
        priority_boost=10
    ),
    HeadlineTemplate(
        template="{winner} Survives {loser} Scare, {score}",
        conditions={"margin": "<=3"},
        sentiment="NEUTRAL",
        priority_boost=15
    ),
    # ... 50+ templates per category
]
```

**Sentiment Analysis**:
- **POSITIVE**: Victories, achievements, signings for contenders
- **NEGATIVE**: Losses, injuries, disappointing performances
- **NEUTRAL**: Routine games, standard transactions
- **HYPE**: Playoff implications, rivalry games, records
- **CRITICAL**: Losing streaks, hot seat situations

**Methods**:
- `generate_headline(event_type: str, event_data: Dict) -> Headline`
- `generate_batch(events: List[Dict]) -> List[Headline]`
- `_analyze_game_significance(game_result: Dict) -> int`
- `_detect_narratives(event_data: Dict) -> List[str]`  # Returns applicable narrative tags

**Acceptance Criteria**:
- [x] 200+ headline templates across all types (201 implemented)
- [x] Conditional template selection based on event data
- [x] Sentiment tagging for all headlines
- [x] Priority scoring for headline ordering
- [x] No duplicate headlines in same week (batch deduplication)
- [x] Unit tests (66 tests passing - exceeded 30 target)

**Implementation Summary**:
- **File Created**: `src/game_cycle/services/headline_generator.py`
- **Test File**: `tests/game_cycle/services/test_headline_generator.py`
- **Template Breakdown**:
  | Type | Count |
  |------|-------|
  | GAME_RECAP | 27 |
  | BLOWOUT | 20 |
  | UPSET | 18 |
  | COMEBACK | 17 |
  | INJURY | 18 |
  | TRADE | 17 |
  | SIGNING | 16 |
  | AWARD | 15 |
  | MILESTONE | 13 |
  | RUMOR | 16 |
  | STREAK | 14 |
  | POWER_RANKING | 10 |
  | **TOTAL** | **201** |

---

### Tollgate 4: Game Recap Narratives ✅ COMPLETE
**Duration**: 3 days
**Goal**: Generate longer-form game recap content

**Enhancement to**: `src/game_cycle/services/headline_generator.py`

**Recap Structure**:
```
[Headline]
[Subheadline with key stat]

[Opening Paragraph - Game summary]
[Key Player Paragraph - Star performances]
[Turning Point Paragraph - Pivotal moment]
[Looking Ahead Paragraph - What's next]

Key Stats:
- {stat1}
- {stat2}
- {stat3}
```

**Data Sources for Recaps**:
- BoxScoresAPI: Final score, quarter scores, team stats
- AnalyticsAPI: Player grades, EPA leaders
- PlayGradesAPI: Key plays (highest graded)
- StandingsAPI: Playoff implications
- RivalryAPI: Rivalry context

**Narrative Elements**:

| Element | Source | Example |
|---------|--------|---------|
| Star Player | Top graded player | "{player} was unstoppable, finishing with {stats}" |
| Turning Point | Highest EPA play | "The game turned in Q3 when {play_description}" |
| Implications | Standings | "With the win, {team} clinches a playoff berth" |
| Rivalry Context | RivalryAPI | "The victory extends {team}'s dominance in this heated rivalry" |
| Streak | Recent results | "{team} has now won 5 straight games" |

**Methods**:
- `generate_game_recap(game_id, dynasty_id) -> GameRecap`
- `_build_opening_paragraph(game_data) -> str`
- `_find_star_player(game_id) -> Dict`
- `_find_turning_point(game_id) -> Dict`
- `_determine_implications(game_data, standings) -> str`

**Acceptance Criteria**:
- [x] Full recap generation for every game (4-paragraph body text)
- [x] Star player identification and stats (using player_game_stats)
- [x] Turning point detection from play grades (with fallback to score summary)
- [x] Playoff implications included when relevant
- [x] Rivalry context integrated
- [x] Unit tests (38 tests passing - exceeded 20 target)
- [x] Fallback body text when APIs unavailable

**Implementation Summary**:
- **File Enhanced**: `src/game_cycle/services/headline_generator.py`
- **Test File**: `tests/game_cycle/services/test_headline_generator_body_text.py`
- **Key Methods Added**:
  - `_gather_recap_data()` - Gather data from all APIs with graceful fallbacks
  - `_generate_opening_paragraph()` - Game summary with final score
  - `_generate_star_players_paragraph()` - Top performers with stats
  - `_generate_turning_point_paragraph()` - Critical play or scoring summary
  - `_generate_looking_ahead_paragraph()` - Playoff implications and next opponent
  - `_generate_body_text()` - Orchestrate 4-paragraph generation
  - `_generate_fallback_body_text()` - Simple body when APIs fail

---

### Tollgate 5: Award Race Coverage ✅ COMPLETE
**Duration**: 3 days
**Goal**: Generate award race narratives and predictions

**Dependency**: Awards System (Milestone 10) - `AwardsAPI`

**New Service**: `src/game_cycle/services/award_race_coverage.py`

**Coverage Types**:

1. **MVP Watch** (Weekly)
   - Top 5 candidates with stats
   - Movement from last week
   - Key performances that helped/hurt case

2. **Rookie Watch** (Weekly)
   - OROY and DROY races
   - Comparison to historical rookies

3. **Award Predictions** (Mid-season, End-season)
   - Projected winners with confidence %
   - Narrative about why they're leading

**Template Examples**:
```python
MVP_TEMPLATES = [
    "{player}'s MVP case grows stronger after {stat_line} performance",
    "Can anyone catch {player}? Another dominant week in the MVP race",
    "{player} stumbles, opening door for {player2} in MVP race",
    "MVP Race Tightens: {player1} and {player2} Separated by Razor-Thin Margin"
]
```

**Integration with AwardsAPI**:
```python
def generate_mvp_coverage(dynasty_id, season, week):
    # Get current award standings
    candidates = AwardsAPI.get_award_race_standings(
        dynasty_id, season, "MVP", week
    )

    # Generate headlines for top movers
    for candidate in candidates[:5]:
        movement = candidate.previous_rank - candidate.current_rank
        if movement >= 2:
            # Generate "rising" headline
        elif movement <= -2:
            # Generate "falling" headline
```

**Methods**:
- `generate_mvp_coverage(dynasty_id, season, week) -> List[Headline]`
- `generate_rookie_coverage(dynasty_id, season, week) -> List[Headline]`
- `generate_award_predictions(dynasty_id, season) -> List[Headline]`
- `_compare_to_historical(player_stats, award_type) -> str`

**Acceptance Criteria**:
- [x] Weekly MVP watch headlines (with movement detection)
- [x] Rookie watch for OROY/DROY (combined coverage)
- [x] Mid-season predictions generated at Week 9
- [x] Award predictions with confidence scoring
- [x] Unit tests (24 tests passing - exceeded 15 target)

**Implementation Summary**:
- **File Created**: `src/game_cycle/services/award_race_coverage.py`
- **Test File**: `tests/game_cycle/services/test_award_race_coverage.py`
- **59 templates** across all coverage types:
  - MVP Leader (6), MVP Rising (6), MVP Falling (5), MVP Tight Race (5), MVP Runaway (5), MVP Newcomer (4)
  - OROY Leader (4), OROY Rising (3), DROY Leader (4), DROY Rising (3), Rookie Combined (3)
  - Mid-Season Prediction (4), Late-Season Prediction (4), Prediction Uncertainty (3)
- **Movement Detection Algorithm**: RISING, FALLING, STABLE, NEW_ENTRY

---

### Tollgate 6: Rumor Mill & Speculation ⏭️ SKIPPED
**Duration**: 3 days
**Goal**: Generate realistic trade rumors and FA speculation

> **Note**: This tollgate was skipped to prioritize UI integration. Can be added in a future iteration.

**New Service**: `src/game_cycle/services/rumor_mill_service.py` (NOT IMPLEMENTED)

**Rumor Types**:

| Type | Trigger | Example |
|------|---------|---------|
| Trade Rumor | Rebuilding team + star player | "Sources: {team} Listening to Offers for {player}" |
| FA Speculation | Expiring contract + contender need | "{player} Reportedly on {team}'s Radar for Free Agency" |
| Coach Hot Seat | 3+ game losing streak | "Heat Intensifying on {coach} After Another Loss" |
| Draft Buzz | Post-season | "{team} Expected to Target {position} in Draft" |

**Acceptance Criteria**:
- [ ] Trade rumors based on team situations
- [ ] FA speculation for expiring contracts
- [ ] Hot seat detection and coverage
- [ ] Draft buzz in offseason
- [ ] Rumors feel realistic (not random)
- [ ] Unit tests (target: 20 tests)

---

### Tollgate 7: UI Integration ✅ COMPLETE
**Duration**: 4 days
**Goal**: Create MediaCoverageView and integrate into game cycle UI

**Files Created**:
- `game_cycle_ui/views/media_coverage_view.py` - Main ESPN-style view
- `game_cycle_ui/widgets/headline_card_widget.py` - Basic headline card
- `game_cycle_ui/widgets/power_rankings_widget.py` - ESPN-styled rankings table
- `game_cycle_ui/widgets/scoreboard_ticker_widget.py` - Horizontal game scores ticker
- `game_cycle_ui/widgets/espn_headline_widget.py` - Featured story + thumbnail grid
- `game_cycle_ui/widgets/breaking_news_widget.py` - Pulsing breaking news banner
- `game_cycle_ui/dialogs/article_detail_dialog.py` - Full article modal dialog

**ESPN-Style MediaCoverageView Structure**:
```
┌─────────────────────────────────────────────────────────────┐
│  [◄] KC 31 - DAL 17 | PHI 28 - NYG 14 | SF 35... [►]       │  <- Scoreboard Ticker
├─────────────────────────────────────────────────────────────┤
│  [BREAKING] Chiefs clinch playoff berth with...             │  <- Breaking News Banner
├─────────────────────────────────────────────────────────────┤
│  NFL COVERAGE                        Week [▼] | [Refresh]   │  <- Header
├─────────────────────────────────────────────────────────────┤
│  [Headlines] [Power Rankings] [Award Watch]                 │  <- ESPN-styled tabs
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐   │
│  │  [GAME RECAP]        TOP STORY                       │   │
│  │  Chiefs Clinch Playoff Berth with Dominant Win       │   │
│  │  Kansas City improves to 10-2 with 35-14 victory... │   │  <- Featured Story
│  └─────────────────────────────────────────────────────┘   │
│  ┌──────────────────────┐ ┌──────────────────────┐        │
│  │ [UPSET] Eagles Win   │ │ [BLOWOUT] Cowboys    │        │   <- Thumbnail Grid
│  │ Jalen Hurts leads... │ │ suffer crushing...   │        │
│  └──────────────────────┘ └──────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

**ESPN Color Theme**:
```python
ESPN_RED = "#cc0000"
ESPN_DARK_BG = "#0d0d0d"
ESPN_CARD_BG = "#1a1a1a"
ESPN_TEXT_PRIMARY = "#FFFFFF"
ESPN_TEXT_SECONDARY = "#888888"
ESPN_BORDER = "#333333"
```

**Tab Structure**:
1. **Headlines Tab**: Featured story + thumbnail grid layout
2. **Power Rankings Tab**: 32-team rankings with tier badges and movement arrows
3. **Award Watch Tab**: MVP race, OROY/DROY standings (placeholder)

**Widget Components**:
- `ScoreboardTickerWidget` - Horizontal scrolling bar with game scores and nav arrows
- `BreakingNewsBanner` - Pulsing red banner for high-priority headlines (rotates up to 5)
- `ESPNFeaturedStoryWidget` - Large featured story card with category badge
- `ESPNThumbnailWidget` - Compact thumbnail cards for secondary stories
- `ESPNHeadlinesGridWidget` - Grid combining featured + 2-column thumbnails
- `PowerRankingsWidget` - ESPN dark-themed table with tier colors

**Acceptance Criteria**:
- [x] MediaCoverageView with 3 tabs (Headlines, Power Rankings, Award Watch)
- [x] ESPN-style dark theme with red accents
- [x] Scoreboard ticker with horizontal scroll and game scores
- [x] Breaking news banner with pulsing animation
- [x] Featured story + thumbnail grid layout
- [x] HeadlineCardWidget with sentiment styling
- [x] PowerRankingsWidget with ESPN-style tier visualization
- [x] ArticleDetailDialog for full content with ESPN styling
- [x] Integration with main_window.py (Media tab added)
- [x] Week selector synced with season state
- [x] Team name display (fixed from "Team 30" issue)
- [x] Player name lookup (fixed from "Player #615" issue)
- [x] Body text generation with fallback

**Implementation Summary**:
- **Total new widget files**: 5
- **Dialog files**: 1
- **View files**: 1
- **Theme updates**: ESPN color constants added to theme.py

---

## Files to Create/Modify

### Backend (New Files)
| File | Purpose |
|------|---------|
| `src/game_cycle/database/media_coverage_api.py` | Database operations for media tables |
| `src/game_cycle/services/power_rankings_service.py` | Weekly power rankings calculation |
| `src/game_cycle/services/headline_generator.py` | Event-driven headline generation |
| `src/game_cycle/services/award_race_coverage.py` | Award race narrative generation |
| `src/game_cycle/services/rumor_mill_service.py` | Trade rumors and speculation |

### Backend (Modify)
| File | Change |
|------|--------|
| `src/game_cycle/database/full_schema.sql` | Add 4 new tables |
| `src/game_cycle/handlers/regular_season.py` | Hook for post-game coverage |
| `src/game_cycle/stage_controller.py` | Week-end coverage generation |

### UI (New Files)
| File | Purpose |
|------|---------|
| `game_cycle_ui/views/media_coverage_view.py` | Main media view |
| `game_cycle_ui/widgets/headline_card_widget.py` | Headline display card |
| `game_cycle_ui/widgets/power_rankings_widget.py` | Rankings table/chart |
| `game_cycle_ui/dialogs/article_detail_dialog.py` | Full article dialog |

### UI (Modify)
| File | Change |
|------|--------|
| `game_cycle_ui/theme.py` | Add sentiment/tier colors |
| `game_cycle_ui/views/__init__.py` | Export MediaCoverageView |
| `game_cycle_ui/main_window.py` | Add Media tab |

### Tests (New Files)
| File | Test Count |
|------|------------|
| `tests/game_cycle/database/test_media_coverage_api.py` | 15 |
| `tests/game_cycle/services/test_power_rankings_service.py` | 20 |
| `tests/game_cycle/services/test_headline_generator.py` | 30 |
| `tests/game_cycle/services/test_award_race_coverage.py` | 15 |
| `tests/game_cycle/services/test_rumor_mill_service.py` | 20 |
| `tests/game_cycle_ui/test_media_coverage_view.py` | 15 |

**Total New Tests**: ~115

---

## Success Criteria

- [ ] Weekly power rankings generated automatically after each week
- [ ] Game recaps generated for all games with star players and turning points
- [ ] Award race coverage updates weekly with movement tracking
- [ ] Trade rumors feel realistic based on team situations
- [ ] MediaCoverageView displays all content types
- [ ] All headlines have sentiment and priority scores
- [ ] ~115 tests passing
- [ ] No performance impact on game simulation
- [ ] Dynasty isolation maintained for all tables

---

## Out of Scope (Future Milestones)

- Social media simulation (Twitter-style feed)
- Fan sentiment tracking
- Press conference mini-game
- Beat reporter relationships
- Media market size effects
- Podcast/radio show simulation
- Historical article archive across seasons

---

## Technical Notes

### Content Generation Strategy

The system uses **template-based generation** rather than LLM generation for:
1. **Consistency**: Same event type produces similar quality
2. **Performance**: No API calls, instant generation
3. **Control**: Predictable output, easy to test
4. **Offline**: Works without internet connection

Templates use variable substitution:
```python
template = "{player} Erupts for {yards} Yards in {team}'s Victory"
headline = template.format(
    player="Patrick Mahomes",
    yards="412",
    team="Kansas City"
)
```

### Headline Priority Algorithm

```python
def calculate_priority(event_type: str, event_data: Dict) -> int:
    """Calculate headline priority (1-100)."""
    base_priority = BASE_PRIORITIES.get(event_type, 50)

    modifiers = 0

    # Significance modifiers
    if event_data.get("is_playoff"):
        modifiers += 20
    if event_data.get("is_rivalry"):
        modifiers += 10
    if event_data.get("is_primetime"):
        modifiers += 5
    if event_data.get("is_record"):
        modifiers += 15
    if event_data.get("margin") and event_data["margin"] >= 21:
        modifiers += 10  # Blowout
    if event_data.get("comeback_points") and event_data["comeback_points"] >= 14:
        modifiers += 15  # Major comeback

    return min(100, base_priority + modifiers)
```

### Integration Hooks

Coverage generation hooks into existing stage transitions:

```python
# In RegularSeasonHandler.handle_week_completion()
def handle_week_completion(self, week: int):
    # Existing logic...

    # Generate media coverage
    MediaCoverageService.generate_week_coverage(
        dynasty_id=self._dynasty_id,
        season=self._season,
        week=week
    )
```

---

## Design Decisions (Confirmed)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Coverage Focus** | Configurable | User can toggle "My Team" vs "League-Wide" view |
| **Tone Level** | ESPN-Style | Balanced but willing to be critical when warranted |
| **Interactivity** | Read-Only | Display generated content only (no press conferences) |
| **Historical Data** | Current Season Only | Generate going forward, not retroactively |

### UI Filter Implementation

The MediaCoverageView will include a toggle:
```
[My Team] [All Teams]  |  Week 12
```

When "My Team" is selected:
- Headlines about user's team appear first (boosted priority)
- Opponent previews and divisional news included
- Other league news appears below in "Around the League" section

When "All Teams" is selected:
- Pure priority-based ordering
- No team filtering applied
