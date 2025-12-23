# Milestone 14: Social Media & Fan Reactions

## Executive Summary

The Social Media & Fan Reactions milestone adds a dynamic "pulse of the fanbase" layer to the simulation through named recurring fan personalities and opinionated media commentators. This creates an always-visible social feed that reacts to games, transactions, and league events with both positive AND negative emotional responses, making the NFL world feel more alive and reactive.

**Core Vision**: Memorable fan characters (e.g., @AlwaysBelievinBill, @SameOldLions, @FireTheCoachJets) create non-repetitive content that users will recognize and remember, providing the emotional temperature of the fanbase at all times.

**Key Innovation**: Unlike the existing Media Coverage system (professional journalism), this adds the raw, emotional, and sometimes irrational reactions of actual fans and hot-take analysts - the voices you'd hear on talk radio and see on social media.

---

## Milestone Placement

Based on the existing milestone structure and dependencies:

- **Recommended Number**: `14_MILESTONE_Social_Media/`
- **Dependencies**: Milestones 1-13 (especially 12: Media Coverage, 10: Awards System, 6: Trade System)
- **Phase**: Enhancement layer (builds on Media Coverage foundation)

**Why After Media Coverage (M12)?**
- Leverages 95% of existing infrastructure (HeadlineGenerator, MediaCoverageAPI, TransactionEvent model)
- Adds the "social" layer (personalities, emotional reactions) on top of professional journalism
- Uses same event triggers but generates fan/media reactions instead of news articles

---

## User Requirements

The feature must satisfy these core requirements:

1. **Location**: Easy to spot, always visible, "in the user's face" ✅
2. **3 UI Location Ideas**: Primary recommendation + 2 alternatives ✅
3. **Emotional Content**: Both positive AND negative reactions ✅
4. **Sources**: Fans AND opinionated media ✅
5. **Topics**: Games AND league rumors ✅
6. **Personalities**: Named recurring characters users will remember ✅
7. **Interaction**: Read-only (owner observes, doesn't respond) ✅

---

## Tollgate Overview

| Tollgate | Name | Status | Dependencies |
|----------|------|--------|--------------|
| 1 | Database Schema + Personality APIs | 🔄 IN PROGRESS | None |
| 2 | Personality Generation Service | ⏳ PLANNED | Tollgate 1 |
| 3 | Post Template System | ⏳ PLANNED | Tollgate 1 |
| 4 | Post Generation Service | ⏳ PLANNED | Tollgates 2, 3 |
| 5 | Integration with Game Events | ⏳ PLANNED | Tollgate 4 |
| 6 | UI Widget Components | ⏳ PLANNED | None (parallel to backend) |
| 7 | Social Feed Container + Main Window Integration | ⏳ PLANNED | Tollgate 6 |
| 8 | Testing + Documentation | ⏳ PLANNED | All tollgates |

**Status**: Milestone in progress - Starting with Tollgate 1

---

## Dependency Flow

```
Tollgate 1: Database Schema + APIs
    │
    ├──► Tollgate 2: Personality Generator ──────┐
    │                                             │
    ├──► Tollgate 3: Post Templates ─────────────┤
    │                                             │
    │                                             ▼
    │                                    Tollgate 4: Post Generator
    │                                             │
    │                                             ▼
    │                                    Tollgate 5: Event Integration
    │
    ├──► Tollgate 6: UI Widgets ─────────────────┐
    │                                             │
    │                                             ▼
    └─────────────────────────────────────► Tollgate 7: Feed Container + Main Window
                                                  │
                                                  ▼
                                           Tollgate 8: Testing + Docs
```

**External Dependencies**:
- Media Coverage (M12): HeadlineGenerator, MediaCoverageAPI, TransactionEvent
- Awards System (M10): Award race events
- Trade System (M6): Transaction events

---

## UI Location - 3 Recommended Approaches

### ⭐ PRIMARY RECOMMENDATION: Right Sidebar Social Feed (300px)

**Placement**: Right edge of main window, parallel to News Rail
**Layout**: `News Rail (200px) | Main Content (~900px) | Social Feed (300px)`
**Visibility**: Always visible, collapsible toggle button

**Pros**:
- ✅ Symmetrical ESPN-style layout
- ✅ Always visible without obscuring content
- ✅ Natural reading flow: Headlines → Content → Reactions
- ✅ Dedicated space for rich post display
- ✅ ESPN.com uses similar right-rail for "Trending"

**Cons**:
- ❌ Reduces main content by 300px (1200px → 900px)
- ❌ May feel cluttered on 1400px window

**Implementation**: Modify `main_window.py` content row from 2-column to 3-column layout

---

### ALTERNATIVE 1: Embedded News Tab

**Placement**: New tab in `MediaCoverageView` (News → Social)
**Visibility**: Only when navigating to News → Social tab

**Pros**: ✅ Zero layout impact, easy to implement
**Cons**: ❌ NOT always visible (violates core requirement)

---

### ALTERNATIVE 2: Bottom Ticker (60px)

**Placement**: Above status bar, horizontal auto-scroll
**Visibility**: Always visible, scrolling marquee

**Pros**: ✅ ESPN broadcast feel, high visibility
**Cons**: ❌ Distracting motion, limited to short posts, accessibility issues

---

## Fan Personality System

### 10 Archetypes (8-12 per team = 256-384 total personalities)

| Archetype | Sentiment Bias | Posting Trigger | Example Handle |
|-----------|----------------|-----------------|----------------|
| Die-Hard Optimist | +0.7 | All events | @AlwaysBelievinBill |
| Pessimist/Doomer | -0.6 | Losses, bad moves | @SameOldLions |
| Bandwagon | +0.6 | Win streaks only | @NewFan49ers |
| Stats Nerd | 0.0 | All events | @AdvancedMetricsGuy |
| Old-Timer | Mixed (-0.2 to +0.3) | All events | @Since1967Packer |
| Hot Head | ±0.8 | Emotional moments | @FIRETHECOACH |
| Meme Lord | +0.5 | Wins, blowouts | @BillsMafiaMemes |
| Trade Analyst | 0.0 | Trades, signings | @CapExpertNYG |
| Conspiracy Theorist | -0.5 | Losses, penalties | @RefWatch2025 |
| Balanced Fan | 0.0 | All events | @RationalRedskin |

**Handle Generation Pattern**: `@{Adjective}{Attribute}{TeamNoun/Year}`

**Examples**:
- @AlwaysBelievinBill (Bills optimist)
- @SameOldLions (Lions pessimist)
- @Since1967Packer (Packers old-timer)
- @FireTheCoachJets (Jets hot head)

---

## Media Personality System

| Type | Count | Scope | Example Handle | Posting Trigger |
|------|-------|-------|----------------|-----------------|
| Beat Reporter | 32 (1/team) | Team-specific | @NYGBeatReporter | Every team game, trade, signing |
| Hot Take Analyst | 5-8 | League-wide | @HotTakeTom | Upsets, blowouts, controversies (50% chance) |
| Stats Nerd/PFF | 3-5 | League-wide | @PFFAnalyst | Weekly grades, stat milestones |

**Total Media Personalities**: 40-45

---

## Tollgate Details

### Tollgate 1: Database Schema + Personality APIs ✅ IN PROGRESS
**Duration**: 2 days
**Goal**: Create database tables and API layer for social personalities and posts

**New Tables**:

```sql
-- Recurring fan and media personalities (256-384 fans + 40-45 media)
CREATE TABLE social_personalities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    handle TEXT NOT NULL,  -- @AlwaysBelievinBill
    display_name TEXT NOT NULL,  -- "Always Believin' Bill"
    personality_type TEXT NOT NULL,  -- 'FAN', 'BEAT_REPORTER', 'HOT_TAKE', 'STATS_ANALYST'
    archetype TEXT,  -- 'OPTIMIST', 'PESSIMIST', 'BANDWAGON', etc. (NULL for media)
    team_id INTEGER,  -- NULL for league-wide media
    sentiment_bias REAL NOT NULL DEFAULT 0.0,  -- -1.0 to 1.0
    posting_frequency TEXT NOT NULL,  -- 'ALL_EVENTS', 'WIN_ONLY', 'EMOTIONAL_MOMENTS'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(dynasty_id, handle)
);

-- Individual posts/reactions from personalities
CREATE TABLE social_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    personality_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,
    post_text TEXT NOT NULL,
    event_type TEXT NOT NULL,  -- 'GAME_RESULT', 'TRADE', 'SIGNING', 'AWARD', 'RUMOR'
    sentiment REAL NOT NULL,  -- -1.0 to 1.0 (personality_bias + event_modifier)
    likes INTEGER DEFAULT 0,  -- Simulated engagement
    retweets INTEGER DEFAULT 0,  -- Simulated engagement
    event_metadata TEXT,  -- JSON: game_id, trade_id, player_id, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (personality_id) REFERENCES social_personalities(id)
);

CREATE INDEX idx_social_posts_dynasty_season_week ON social_posts(dynasty_id, season, week);
CREATE INDEX idx_social_posts_personality ON social_posts(personality_id);
CREATE INDEX idx_social_posts_event_type ON social_posts(event_type);
CREATE INDEX idx_social_personalities_dynasty ON social_personalities(dynasty_id);
CREATE INDEX idx_social_personalities_team ON social_personalities(team_id);
```

**New API Classes**:

1. **`src/game_cycle/database/social_personalities_api.py`**

```python
class SocialPersonalityAPI:
    """CRUD operations for social personalities."""

    def create_personality(
        self,
        dynasty_id: str,
        handle: str,
        display_name: str,
        personality_type: str,  # 'FAN', 'BEAT_REPORTER', etc.
        archetype: Optional[str],
        team_id: Optional[int],
        sentiment_bias: float,
        posting_frequency: str
    ) -> int:
        """Create new personality, return ID."""

    def get_personalities_by_team(
        self,
        dynasty_id: str,
        team_id: int,
        personality_type: Optional[str] = None
    ) -> List[Dict]:
        """Get all personalities for a team."""

    def get_league_wide_personalities(
        self,
        dynasty_id: str,
        personality_type: Optional[str] = None
    ) -> List[Dict]:
        """Get league-wide media personalities."""

    def get_personality_by_handle(
        self,
        dynasty_id: str,
        handle: str
    ) -> Optional[Dict]:
        """Look up personality by @handle."""
```

2. **`src/game_cycle/database/social_posts_api.py`**

```python
class SocialPostsAPI:
    """CRUD and feed operations for social posts."""

    def create_post(
        self,
        dynasty_id: str,
        personality_id: int,
        season: int,
        week: int,
        post_text: str,
        event_type: str,
        sentiment: float,
        likes: int = 0,
        retweets: int = 0,
        event_metadata: Optional[Dict] = None
    ) -> int:
        """Create new post, return ID."""

    def get_rolling_feed(
        self,
        dynasty_id: str,
        season: int,
        week: int,
        limit: int = 20,
        offset: int = 0,
        team_filter: Optional[int] = None,
        event_type_filter: Optional[str] = None,
        sentiment_filter: Optional[str] = None  # 'POSITIVE', 'NEGATIVE', 'NEUTRAL'
    ) -> List[Dict]:
        """Get chronological feed of posts with filters."""

    def get_posts_by_personality(
        self,
        personality_id: int,
        limit: int = 20
    ) -> List[Dict]:
        """Get recent posts from a specific personality."""

    def get_event_posts(
        self,
        dynasty_id: str,
        event_type: str,
        event_metadata: Dict
    ) -> List[Dict]:
        """Get all posts about a specific event (e.g., game_id=123)."""
```

**Files to Create**:
- `src/game_cycle/database/social_personalities_api.py`
- `src/game_cycle/database/social_posts_api.py`

**Files to Modify**:
- `src/game_cycle/database/schema.sql` (add 2 new tables)

**Acceptance Criteria**:
- [ ] Both tables created in schema.sql
- [ ] SocialPersonalityAPI with 4 public methods
- [ ] SocialPostsAPI with 4 public methods
- [ ] Dynasty isolation enforced (all queries filter by dynasty_id)
- [ ] Unit tests for CRUD operations (target: 20 tests)
- [ ] Handle uniqueness constraint working

---

### Tollgate 2: Personality Generation Service
**Duration**: 2 days
**Goal**: Generate 256-384 recurring fan personalities and 40-45 media personalities

**New Service**: `src/game_cycle/services/personality_generator.py`

**Generation Algorithm**:
1. For each team (1-32):
   - Generate 8-12 fan personalities (random selection from 10 archetypes)
   - Generate 1 beat reporter
2. Generate 5-8 hot-take analysts (league-wide)
3. Generate 3-5 stats nerds (league-wide)

**Name Template System**: `src/config/social_media/fan_name_templates.json`

```json
{
  "fan_name_templates": {
    "optimist": [
      "@AlwaysBelievin{TeamNickname}",
      "@{TeamNickname}ForLife",
      "@Eternal{TeamNickname}Faith",
      "@Never{TeamNickname}Doubt"
    ],
    "pessimist": [
      "@SameOld{TeamNickname}",
      "@{TeamNickname}Misery",
      "@Why{TeamNickname}Why",
      "@Cursed{TeamNickname}Fan"
    ],
    "bandwagon": [
      "@NewFan{TeamNickname}",
      "@{TeamNickname}Since{RecentYear}",
      "@Just{TeamNickname}Things"
    ],
    "stats_nerd": [
      "@{TeamNickname}Analytics",
      "@AdvancedMetrics{TeamNickname}",
      "@{TeamNickname}FilmRoom"
    ],
    "old_timer": [
      "@Since{FoundedYear}{TeamNickname}",
      "@Old{TeamNickname}Fan",
      "@Remember{LegendName}"
    ],
    "hot_head": [
      "@FIRETHECOACH{TeamNickname}",
      "@{TeamNickname}RAGE",
      "@ANGRY{TeamNickname}FAN"
    ],
    "meme_lord": [
      "@{TeamNickname}Mafia",
      "@{TeamNickname}Memes",
      "@Dank{TeamNickname}Memes"
    ],
    "trade_analyst": [
      "@CapExpert{TeamAbbrev}",
      "@{TeamNickname}TradeWatch",
      "@{TeamNickname}Insider"
    ],
    "conspiracy": [
      "@RefWatch{TeamAbbrev}",
      "@{TeamNickname}Conspiracy",
      "@Rigged{TeamNickname}"
    ],
    "balanced": [
      "@Rational{TeamNickname}",
      "@Fair{TeamNickname}Fan",
      "@Objective{TeamNickname}"
    ]
  },
  "media_templates": {
    "beat_reporter": "@{TeamAbbrev}BeatReporter",
    "hot_take": [
      "@HotTakeTom",
      "@FirstTakeNFL",
      "@SkipAnalogNFL"
    ],
    "stats_analyst": [
      "@PFFAnalyst",
      "@NFLStatHead",
      "@AdvancedNFLMetrics"
    ]
  }
}
```

**Methods**:
- `generate_all_personalities(dynasty_id: str) -> Dict[str, int]`
- `_generate_team_fans(dynasty_id, team_id) -> List[Dict]`
- `_generate_beat_reporter(dynasty_id, team_id) -> Dict`
- `_generate_league_wide_media(dynasty_id) -> List[Dict]`
- `_create_handle(archetype, team_id) -> str`

**Files to Create**:
- `src/game_cycle/services/personality_generator.py`
- `src/config/social_media/fan_name_templates.json`

**Acceptance Criteria**:
- [ ] All 32 teams have 8-12 unique fans
- [ ] All handles are unique within dynasty
- [ ] 256-384 total fan personalities created
- [ ] 40-45 media personalities created
- [ ] Unit tests (target: 15 tests)

---

### Tollgate 3: Post Template System
**Duration**: 3 days
**Goal**: Create 100+ post templates for all event types with variable substitution

**Template Configuration**: `src/config/social_media/post_templates.json`

```json
{
  "game_result_win": {
    "optimist": [
      "LET'S GOOOOO! {team} {verb} {opponent} {score}! {emoji}",
      "THAT'S MY TEAM! {player} was absolutely incredible today!",
      "Can't stop this {team} team right now! Playoff bound baby! {emoji}"
    ],
    "pessimist": [
      "Finally. About time. Still don't trust them.",
      "Cool we won but this team will find a way to disappoint us.",
      "One win doesn't erase the last {losing_streak} losses."
    ],
    "stats_nerd": [
      "{player} posted a {grade} PFF grade with {stat}. Elite performance.",
      "Win probability was only {win_prob}% at halftime. Incredible comeback.",
      "{team} now leads the league in {stat_category}. Sustainable?"
    ]
  },
  "game_result_loss": {
    "optimist": [
      "Tough loss but we'll bounce back! Still believe! {emoji}",
      "Close game, just didn't go our way. On to the next one.",
      "Proud of the fight. {player} gave it his all."
    ],
    "pessimist": [
      "I KNEW IT. SAME OLD {team}. FIRE EVERYONE.",
      "This team is a joke. Absolutely pathetic.",
      "Why do I even watch anymore? Pain."
    ],
    "hot_head": [
      "FIRE {coach}!!!! THIS IS UNACCEPTABLE!!!!",
      "REFS STOLE THIS GAME. RIGGED. {emoji_angry}",
      "I'M DONE WITH THIS TEAM. SEASON OVER."
    ]
  },
  "trade": {
    "optimist": [
      "LOVE this move! {player} is exactly what we needed! {emoji}",
      "GM is cooking! This pushes us over the edge!",
      "Championship window OPEN! Let's gooo!"
    ],
    "pessimist": [
      "We gave up WAY too much for {player}. Terrible trade.",
      "This team is allergic to good decisions.",
      "Can't wait for this to blow up in our faces."
    ],
    "trade_analyst": [
      "{team} gets: {player} | Cap hit: ${cap_hit}M | Grade: {grade}",
      "Smart move. {player} fills the {position} hole without breaking the bank.",
      "Overpay. {player} isn't worth a {draft_pick}. Bad asset management."
    ]
  },
  "signing": {
    "optimist": [
      "YES! Locked up {player}! {years}yr/${value}M is a STEAL!",
      "Best news all offseason! {player} staying put! {emoji}",
      "This is why I love this front office. Nailed it."
    ],
    "pessimist": [
      "${value}M for {player}??? Are we insane???",
      "Way too much money. This will cripple our cap.",
      "Classic {team} overpaying for a declining player."
    ]
  },
  "award": {
    "all": [
      "LETS GOOOO {player} MVP!!!! {emoji}{emoji}{emoji}",
      "Congrats to {player}! Well deserved!",
      "{player} for MVP! No debate!",
      "If {player} doesn't win MVP this league is rigged.",
      "About time {player} gets some respect! MVP!"
    ]
  }
}
```

**Template Loader Service**: `src/game_cycle/services/post_template_loader.py`

**Methods**:
- `load_templates() -> Dict[str, Dict[str, List[str]]]`
- `get_template(event_type: str, archetype: str, sentiment: str) -> str`
- `fill_template(template: str, variables: Dict) -> str`
- `_select_random_template(templates: List[str], anti_repeat_buffer: List[str]) -> str`

**Anti-Repetition Logic**: Track last 10 templates used by each personality, never repeat

**Files to Create**:
- `src/config/social_media/post_templates.json`
- `src/game_cycle/services/post_template_loader.py`

**Acceptance Criteria**:
- [ ] 100+ templates total across all event types
- [ ] Templates cover: GAME_RESULT, TRADE, SIGNING, AWARD, RUMOR
- [ ] Variable substitution working ({team}, {player}, {score}, etc.)
- [ ] Anti-repetition buffer prevents duplicates
- [ ] Unit tests (target: 15 tests)

---

### Tollgate 4: Post Generation Service
**Duration**: 3 days
**Goal**: Main post generation engine with event-to-post mapping

**New Service**: `src/game_cycle/services/social_post_generator.py`

**Post Count Mapping**:
| Event Type | Post Count | Selection Logic |
|------------|------------|-----------------|
| Normal Game Win | 4-6 posts | 80% team fans, 10% opponent fans, 10% media |
| Normal Game Loss | 4-6 posts | 70% team fans (negative), 20% opponent fans, 10% media |
| Upset Win | 8-12 posts | 60% winning team, 30% losing team, 10% hot-take media |
| Blowout | 6-10 posts | 50% winning team, 40% losing team, 10% media |
| Trade | 3-5 posts | Both teams' trade analysts + 1-2 hot takes |
| Big Signing | 3-5 posts | Team fans + cap analysts |
| Award Announcement | 2-4 posts | Winning team fans + league-wide media |

**Engagement Calculator**:
```python
def calculate_engagement(event_magnitude: int, sentiment: float) -> Tuple[int, int]:
    """Calculate likes and retweets based on event importance."""
    base_likes = event_magnitude * 10  # 0-100
    base_retweets = event_magnitude * 3  # 0-30

    # Extreme sentiment (very positive or negative) drives more engagement
    sentiment_boost = abs(sentiment) * 50

    likes = base_likes + random.randint(0, int(sentiment_boost))
    retweets = base_retweets + random.randint(0, int(sentiment_boost // 3))

    return (likes, retweets)
```

**80/20 Recurring/Random Mix**:
- 80% of posts: From named recurring personalities
- 20% of posts: From randomly generated one-off fans (e.g., "@RandomBillsFan2025")

**Methods**:
- `generate_game_posts(game_id, dynasty_id) -> List[Dict]`
- `generate_transaction_posts(event_type, event_data, dynasty_id) -> List[Dict]`
- `generate_award_posts(award_data, dynasty_id) -> List[Dict]`
- `_select_posting_personalities(event_data) -> List[int]`
- `_calculate_post_sentiment(personality_bias, event_outcome) -> float`

**Files to Create**:
- `src/game_cycle/services/social_post_generator.py`

**Acceptance Criteria**:
- [ ] Generate 4-8 posts per normal game
- [ ] Generate 8-12 posts per upset/blowout
- [ ] 80/20 recurring/random ratio maintained
- [ ] Sentiment varies based on personality bias + event outcome
- [ ] Engagement (likes/retweets) calculated based on magnitude
- [ ] Unit tests (target: 20 tests)

---

### Tollgate 5: Integration with Game Events
**Duration**: 2 days
**Goal**: Hook post generation into regular season, offseason, and awards

**Integration Points**:

1. **Post-Game (RegularSeasonHandler)**:
```python
# In src/game_cycle/handlers/regular_season.py
def _execute_week(self, week: int):
    # ... existing game simulation ...

    # Generate social media posts for all games
    for game_id in week_games:
        posts = SocialPostGenerator.generate_game_posts(
            game_id=game_id,
            dynasty_id=self._dynasty_id
        )
        for post_data in posts:
            self._social_posts_api.create_post(**post_data)
```

2. **Transactions (OffseasonHandler)**:
```python
# In src/game_cycle/handlers/offseason.py
def _handle_trade(self, trade_data: Dict):
    # ... existing trade logic ...

    # Generate social posts about trade
    posts = SocialPostGenerator.generate_transaction_posts(
        event_type='TRADE',
        event_data=trade_data,
        dynasty_id=self._dynasty_id
    )
    for post_data in posts:
        self._social_posts_api.create_post(**post_data)
```

3. **Awards (AwardsService)**:
```python
# Hook into award announcement
posts = SocialPostGenerator.generate_award_posts(
    award_data={'award': 'MVP', 'player_id': mvp_id},
    dynasty_id=self._dynasty_id
)
```

**Files to Modify**:
- `src/game_cycle/handlers/regular_season.py`
- `src/game_cycle/handlers/offseason.py`

**Acceptance Criteria**:
- [ ] Posts generated after every game (<0.5s overhead)
- [ ] Posts generated for trades, signings, cuts
- [ ] Posts generated for award announcements
- [ ] No performance degradation to game simulation
- [ ] Integration tests (target: 10 tests)

---

### Tollgate 6: UI Widget Components
**Duration**: 3 days
**Goal**: Create reusable widgets for displaying social posts

**Widget Files to Create**:

1. **`game_cycle_ui/widgets/social_post_card.py`** - Individual post display

```python
class SocialPostCard(QWidget):
    """Single social media post card."""

    def __init__(self, post_data: Dict, parent=None):
        # Layout:
        # - Avatar icon (FAN/MEDIA badge)
        # - Handle (@AlwaysBelievinBill) + Display name
        # - Post text
        # - Engagement bar (likes/retweets)
        # - Timestamp
```

2. **`game_cycle_ui/widgets/personality_badge.py`** - FAN/MEDIA pill badge

```python
class PersonalityBadge(QLabel):
    """Colored badge showing personality type."""

    COLORS = {
        'FAN': '#1E90FF',  # Blue
        'BEAT_REPORTER': '#FFD700',  # Gold
        'HOT_TAKE': '#FF4500',  # Orange-red
        'STATS_ANALYST': '#32CD32'  # Green
    }
```

3. **`game_cycle_ui/widgets/reaction_bar.py`** - Likes/retweets display

```python
class ReactionBar(QWidget):
    """Horizontal bar showing likes and retweets."""

    def __init__(self, likes: int, retweets: int, parent=None):
        # ❤️ 42    🔁 12
```

4. **`game_cycle_ui/widgets/social_filter_bar.py`** - Team/type/sentiment filters

```python
class SocialFilterBar(QWidget):
    """Filter controls for social feed."""

    # [All Teams ▼] [All Types ▼] [All Sentiments ▼]

    team_filter_changed = Signal(int)  # team_id or None
    type_filter_changed = Signal(str)  # 'FAN', 'MEDIA', or None
    sentiment_filter_changed = Signal(str)  # 'POSITIVE', 'NEGATIVE', or None
```

**Files to Create**:
- `game_cycle_ui/widgets/social_post_card.py`
- `game_cycle_ui/widgets/personality_badge.py`
- `game_cycle_ui/widgets/reaction_bar.py`
- `game_cycle_ui/widgets/social_filter_bar.py`

**Acceptance Criteria**:
- [ ] All widgets use ESPN dark theme
- [ ] SocialPostCard renders cleanly with word wrap
- [ ] PersonalityBadge uses correct colors per type
- [ ] ReactionBar displays engagement counts
- [ ] SocialFilterBar emits signals on filter change
- [ ] UI tests (target: 10 tests)

---

### Tollgate 7: Social Feed Container + Main Window Integration
**Duration**: 3 days
**Goal**: Create main feed widget and integrate into right sidebar

**Main Feed Widget**: `game_cycle_ui/widgets/social_feed_widget.py`

```python
class SocialFeedWidget(QWidget):
    """Main social media feed container (300px right sidebar)."""

    def __init__(self, db_path: str, dynasty_id: str, parent=None):
        # Layout:
        # - Header: "Fan Reactions" + collapse button
        # - SocialFilterBar (team/type/sentiment)
        # - QScrollArea with SocialPostCards (20 per load)
        # - "Load More" button (pagination)

    def load_feed(self, season: int, week: int):
        """Load posts from SocialPostsAPI."""
        posts = self._api.get_rolling_feed(
            dynasty_id=self._dynasty_id,
            season=season,
            week=week,
            limit=20,
            offset=self._current_offset,
            team_filter=self._team_filter,
            event_type_filter=self._type_filter,
            sentiment_filter=self._sentiment_filter
        )
        for post in posts:
            card = SocialPostCard(post)
            self._feed_layout.addWidget(card)
```

**Main Window Integration**: Modify `game_cycle_ui/main_window.py`

```python
# Current layout: News Rail (200px) | Main Content (1200px)
# New layout: News Rail (200px) | Main Content (900px) | Social Feed (300px)

def _create_content_row(self):
    content_row = QHBoxLayout()

    # Left: News Rail (existing)
    self._news_rail = NewsRailWidget(...)
    content_row.addWidget(self._news_rail)

    # Center: Main content (existing)
    self._content_stack = QStackedWidget()
    content_row.addWidget(self._content_stack, stretch=1)

    # Right: Social Feed (NEW)
    self._social_feed = SocialFeedWidget(
        db_path=self._db_path,
        dynasty_id=self._dynasty_id
    )
    self._social_feed.setFixedWidth(300)
    content_row.addWidget(self._social_feed)

    return content_row
```

**Collapse/Expand Toggle**: Small button to hide/show sidebar

**Files to Create**:
- `game_cycle_ui/widgets/social_feed_widget.py`

**Files to Modify**:
- `game_cycle_ui/main_window.py` (add 3-column layout)

**Acceptance Criteria**:
- [ ] Social feed always visible on right edge (300px)
- [ ] Feed scrolls with 20 posts per page
- [ ] "Load More" button fetches next 20 posts
- [ ] Filters work correctly (team/type/sentiment)
- [ ] Collapse button hides sidebar
- [ ] No layout issues on 1400px window
- [ ] UI tests (target: 10 tests)

---

### Tollgate 8: Testing + Documentation
**Duration**: 2 days
**Goal**: Comprehensive testing and demo script

**Test Files to Create**:

1. **`tests/test_game_cycle/services/test_social_post_generator.py`** (20 tests)
   - Test post generation for all event types
   - Test 80/20 recurring/random ratio
   - Test sentiment calculation
   - Test engagement calculation

2. **`tests/test_game_cycle/services/test_personality_generator.py`** (15 tests)
   - Test fan personality generation (8-12 per team)
   - Test media personality generation
   - Test handle uniqueness
   - Test archetype distribution

3. **`tests/test_game_cycle/integration/test_social_feed_integration.py`** (15 tests)
   - Test end-to-end: game → posts generated → feed displays
   - Test 50-game season (no duplicate posts from same personality)
   - Test dynasty isolation

**Demo Script**: `demos/social_feed_demo.py`

```python
# Simulate 1 game week + show social feed output
# Should generate ~40-50 posts (4-6 per game for 8 games)
```

**Documentation**: Already created in this file!

**Files to Create**:
- `tests/test_game_cycle/services/test_social_post_generator.py`
- `tests/test_game_cycle/services/test_personality_generator.py`
- `tests/test_game_cycle/integration/test_social_feed_integration.py`
- `demos/social_feed_demo.py`

**Acceptance Criteria**:
- [ ] All unit tests passing (50+ tests total)
- [ ] Integration test: 50-game season with no duplicate posts
- [ ] Demo script generates realistic feed
- [ ] Documentation complete in this PLAN.md

---

## Files to Create/Modify

### Backend (New Files)
| File | Purpose |
|------|---------|
| `src/game_cycle/database/social_personalities_api.py` | Personality CRUD operations |
| `src/game_cycle/database/social_posts_api.py` | Post CRUD and feed queries |
| `src/game_cycle/services/personality_generator.py` | Generate 256-384 recurring fans + media |
| `src/game_cycle/services/post_template_loader.py` | Template system with anti-repetition |
| `src/game_cycle/services/social_post_generator.py` | Main post generation engine |
| `src/config/social_media/fan_name_templates.json` | 100+ name patterns |
| `src/config/social_media/post_templates.json` | 100+ post templates |

### Backend (Modify)
| File | Change |
|------|--------|
| `src/game_cycle/database/schema.sql` | Add 2 new tables (social_personalities, social_posts) |
| `src/game_cycle/handlers/regular_season.py` | Hook post-game post generation |
| `src/game_cycle/handlers/offseason.py` | Hook transaction post generation |

### UI (New Files)
| File | Purpose |
|------|---------|
| `game_cycle_ui/widgets/social_feed_widget.py` | Main 300px sidebar container |
| `game_cycle_ui/widgets/social_post_card.py` | Individual post rendering |
| `game_cycle_ui/widgets/personality_badge.py` | FAN/MEDIA badge component |
| `game_cycle_ui/widgets/reaction_bar.py` | Likes/retweets display |
| `game_cycle_ui/widgets/social_filter_bar.py` | Team/type/sentiment filters |

### UI (Modify)
| File | Change |
|------|--------|
| `game_cycle_ui/main_window.py` | Add right sidebar (3-column layout) |

### Tests (New Files)
| File | Test Count |
|------|------------|
| `tests/test_game_cycle/services/test_social_post_generator.py` | 20 |
| `tests/test_game_cycle/services/test_personality_generator.py` | 15 |
| `tests/test_game_cycle/integration/test_social_feed_integration.py` | 15 |

**Total New Tests**: ~50

---

## Success Metrics

**User Experience**:
- ✅ Feed feels alive (posts after every game, transaction, award)
- ✅ Recognize recurring fans (@AlwaysBelievinBill becomes a familiar character)
- ✅ See both positive AND negative reactions (not just cheerleading)
- ✅ Always visible in right sidebar (no hunting for it)
- ✅ 50+ games without exact duplicate posts from same personality

**Technical**:
- Post generation <0.5s overhead per event
- Feed loads <1s (20 posts with pagination)
- 256-384 unique recurring fan personalities
- 40-45 media personalities
- 80/20 recurring/random ratio maintained
- Dynasty isolation enforced

---

## Out of Scope (Future Enhancements)

- **User Interaction**: Replying to posts, liking, blocking personalities (read-only for now)
- **Trending Topics**: Hashtag tracking, viral posts
- **Personality Evolution**: Personalities changing sentiment over time based on team performance
- **Historical Feed**: Archive posts across multiple seasons
- **Meme Generation**: Actual image memes, not just text
- **Video Reactions**: Links to simulated reaction videos
- **Cross-Dynasty Sharing**: Famous personalities appearing in multiple dynasties

---

## Technical Notes

### Why Template-Based vs LLM Generation?

Similar to Media Coverage (M12), we use **template-based generation** for:
1. **Performance**: No API calls, instant generation
2. **Consistency**: Predictable quality and tone
3. **Control**: Can tune sentiment and variety precisely
4. **Offline**: Works without internet connection
5. **Cost**: Free vs. expensive LLM API costs for every event

### Personality Sentiment Calculation

```python
def calculate_post_sentiment(
    personality_bias: float,  # -1.0 to 1.0 (archetype baseline)
    event_outcome: str,  # 'WIN', 'LOSS', 'NEUTRAL'
    event_magnitude: int  # 0-100 (importance)
) -> float:
    """Calculate final post sentiment."""

    # Base event sentiment
    event_sentiment = {
        'WIN': +0.8,
        'LOSS': -0.8,
        'NEUTRAL': 0.0
    }[event_outcome]

    # Weight: 60% event, 40% personality
    final = (event_sentiment * 0.6) + (personality_bias * 0.4)

    # Extreme personalities amplify emotion for big events
    if abs(personality_bias) > 0.6 and event_magnitude > 70:
        final *= 1.3  # Hot heads and doomers go EXTRA

    return max(-1.0, min(1.0, final))
```

### Anti-Repetition Algorithm

Each personality tracks last 10 templates used:

```python
# Stored in memory cache (not persisted)
personality_template_history = {
    personality_id: deque(maxlen=10)  # Last 10 template IDs
}

def select_template(personality_id, available_templates):
    recent = personality_template_history[personality_id]

    # Filter out recently used templates
    fresh_templates = [t for t in available_templates if t.id not in recent]

    if not fresh_templates:
        # All used recently, reset and use any
        fresh_templates = available_templates
        recent.clear()

    selected = random.choice(fresh_templates)
    recent.append(selected.id)
    return selected
```

This ensures no personality uses the same template twice in their last 10 posts, preventing "I've seen this before" feeling even in a 50-game season.

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **UI Location** | Right Sidebar (300px) | Always visible, symmetrical layout, ESPN-style |
| **Personality Mix** | 80% recurring, 20% random | Balance familiarity with variety |
| **Interaction** | Read-Only | Owner observes but doesn't engage (stays in role) |
| **Sentiment Range** | -1.0 to +1.0 | Allows nuanced reactions, not just binary good/bad |
| **Post Count** | 4-8 normal, 8-12 upset | Scales with event importance |
| **Media Scope** | Beat reporters (team) + Analysts (league) | Mirrors real NFL media ecosystem |

---

## Existing Infrastructure (95% Already Built!)

**From Media Coverage (M12)**:
- `HeadlineGenerator`: 12+ headline types, 200+ templates, sentiment analysis
- `MediaCoverageAPI.get_rolling_headlines()`: Chronological feed logic
- `media_headlines` table: Headline storage pattern
- `TransactionEvent` model: Standardized event triggers

**From Awards System (M10)**:
- `AwardsAPI`: Award race data, MVP candidates
- Award announcement events

**From Trade System (M6)**:
- `TradeService`: Trade completion events
- Transaction history tracking

**What We're Adding**:
- The "social" layer: Personalities, emotional reactions, @handles
- Post templates (shorter, more casual than headlines)
- Engagement simulation (likes/retweets)
- Always-visible feed UI (not buried in a tab)

---

## Implementation Priority

**Week 1 (Tollgates 1-3)**: Backend foundation
- Database schema + APIs
- Personality generation
- Post templates

**Week 2 (Tollgates 4-5)**: Post generation + integration
- Main generation engine
- Hook into game events

**Week 3 (Tollgates 6-7)**: UI
- Widget components
- Feed container + main window integration

**Week 4 (Tollgate 8)**: Testing + polish
- Comprehensive tests
- Demo script
- Bug fixes

**Total Estimated Duration**: 4 weeks
