# Milestone #6: Player Personas and Preferences

## Overview

Implement a player personality system where each player has unique preferences that influence their decisions during free agency, contract negotiations, and trade scenarios. This creates realistic market dynamics where not every player goes to the highest bidder.

**Scope**: Free Agency, Re-signing, Trade Veto (Draft preferences deferred to future milestone)

---

## Progress Summary

| Tollgate | Status | Tests |
|----------|--------|-------|
| 1. Core Data Models | ✅ COMPLETE | 71/71 |
| 2. Static Team Data | ✅ COMPLETE | 11/11 |
| 3. Persona Service | ✅ COMPLETE | 18/18 |
| 4. Team Attractiveness Service | ✅ COMPLETE | 18/18 |
| 5. Preference Engine | ✅ COMPLETE | 41/41 |
| 6. Free Agency Integration | ✅ COMPLETE | 18/18 |
| 7. Re-signing Integration | ✅ COMPLETE | 8/8 |
| 8. Trade Veto & UI | ⏹ NOT STARTED | 0/? |

**Total Tests**: 185 passing

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Visibility | Partially visible, more for own team | Hints shown to all; full details for your roster |
| Determinism | Money Override | Probabilistic with money as ultimate override |
| Draft Day | Deferred | Focus on FA/trades first |
| Contender History | 5-year window | Realistic memory for playoff success tracking |

---

## Architecture

Follow existing codebase pattern:
```
Archetype (Data Model) → Modifiers (Business Logic) → Service Layer → Database API
```

**Reference Implementations:**
- `src/team_management/gm_archetype.py` - GMArchetype dataclass (11 traits, 0.0-1.0 scale)
- `src/transactions/personality_modifiers.py` - PersonalityModifiers class (1078 lines)

---

## Data Models

### 1. PersonaType Enum

**File:** `src/player_management/player_persona.py`

```python
class PersonaType(Enum):
    RING_CHASER = "ring_chaser"       # Prioritizes contenders, takes less to win
    HOMETOWN_HERO = "hometown_hero"   # Prefers birthplace/college area, loyal to drafting team
    MONEY_FIRST = "money_first"       # Always follows highest offer
    BIG_MARKET = "big_market"         # Wants LA, NYC, Dallas - media exposure
    SMALL_MARKET = "small_market"     # Prefers quieter markets, less pressure
    LEGACY_BUILDER = "legacy_builder" # Wants to stay with one team, be franchise icon
    COMPETITOR = "competitor"         # Wants playing time, avoids bench roles
    SYSTEM_FIT = "system_fit"         # Prioritizes schemes matching skills
```

### 2. PlayerPersona Dataclass

```python
@dataclass
class PlayerPersona:
    player_id: int
    persona_type: PersonaType

    # Preference weights (0-100 scale)
    money_importance: int = 50
    winning_importance: int = 50
    location_importance: int = 50
    playing_time_importance: int = 50
    loyalty_importance: int = 50
    market_size_importance: int = 50
    coaching_fit_importance: int = 50
    relationships_importance: int = 50

    # Biographical data (for Hometown Hero)
    birthplace_state: Optional[str] = None
    college_state: Optional[str] = None
    drafting_team_id: Optional[int] = None

    # Career context (dynamically updated)
    career_earnings: int = 0
    championship_count: int = 0
    pro_bowl_count: int = 0
```

### 3. TeamAttractiveness Dataclass

**File:** `src/player_management/team_attractiveness.py`

```python
@dataclass
class TeamAttractiveness:
    team_id: int

    # Static factors (from config)
    market_size: int              # 1-100 (NYC=95, Green Bay=25)
    state_income_tax_rate: float  # 0.0-0.13 (Texas=0, California=0.13)
    weather_score: int            # 1-100 (Miami=85, Green Bay=30)

    # Dynamic factors (computed each season)
    playoff_appearances_5yr: int  # 0-5
    super_bowl_wins_5yr: int      # 0-5
    winning_culture_score: int    # Computed from 5-year record
    coaching_prestige: int        # Based on coach tenure/success
    current_season_wins: int
    current_season_losses: int

    @property
    def contender_score(self) -> int:
        """0-100 score for how much of a contender this team is."""
        pass
```

---

## Database Schema

**File:** `src/game_cycle/database/schema.sql`

```sql
-- Player Personas Table
CREATE TABLE IF NOT EXISTS player_personas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    player_id INTEGER NOT NULL,

    -- Primary persona type
    persona_type TEXT NOT NULL CHECK(persona_type IN (
        'ring_chaser', 'hometown_hero', 'money_first', 'big_market',
        'small_market', 'legacy_builder', 'competitor', 'system_fit'
    )),

    -- Preference weights (0-100)
    money_importance INTEGER DEFAULT 50,
    winning_importance INTEGER DEFAULT 50,
    location_importance INTEGER DEFAULT 50,
    playing_time_importance INTEGER DEFAULT 50,
    loyalty_importance INTEGER DEFAULT 50,
    market_size_importance INTEGER DEFAULT 50,
    coaching_fit_importance INTEGER DEFAULT 50,
    relationships_importance INTEGER DEFAULT 50,

    -- Biographical data
    birthplace_state TEXT,
    college_state TEXT,
    drafting_team_id INTEGER,

    -- Career context (updated during career)
    career_earnings INTEGER DEFAULT 0,
    championship_count INTEGER DEFAULT 0,
    pro_bowl_count INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, player_id)
);

-- Team Attractiveness (5-year history tracking)
CREATE TABLE IF NOT EXISTS team_attractiveness (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
    season INTEGER NOT NULL,

    -- Dynamic factors (updated each season)
    playoff_appearances_5yr INTEGER DEFAULT 0,
    super_bowl_wins_5yr INTEGER DEFAULT 0,
    winning_culture_score INTEGER DEFAULT 50,
    coaching_prestige INTEGER DEFAULT 50,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(dynasty_id, team_id, season)
);

-- Season Results History (for 5-year window calculations)
CREATE TABLE IF NOT EXISTS team_season_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    team_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    wins INTEGER NOT NULL,
    losses INTEGER NOT NULL,
    made_playoffs BOOLEAN DEFAULT FALSE,
    playoff_round_reached TEXT,  -- 'wild_card', 'divisional', 'conference', 'super_bowl'
    won_super_bowl BOOLEAN DEFAULT FALSE,

    UNIQUE(dynasty_id, team_id, season)
);

CREATE INDEX idx_personas_dynasty ON player_personas(dynasty_id);
CREATE INDEX idx_personas_player ON player_personas(dynasty_id, player_id);
CREATE INDEX idx_team_history ON team_season_history(dynasty_id, team_id, season);
```

---

## Static Team Data

**File:** `src/config/team_attractiveness_static.json`

```json
{
  "1": {
    "team_id": 1,
    "name": "Buffalo Bills",
    "market_size": 35,
    "state": "NY",
    "state_income_tax_rate": 0.0882,
    "weather_score": 25,
    "metro_population": 1100000
  },
  "10": {
    "team_id": 10,
    "name": "Dallas Cowboys",
    "market_size": 90,
    "state": "TX",
    "state_income_tax_rate": 0.0,
    "weather_score": 70,
    "metro_population": 7600000
  }
}
```

**No-Tax States:** TX, FL, TN, WA, NV (Las Vegas Raiders, Titans, Jaguars, Buccaneers, Dolphins, Cowboys, Texans, Seahawks)

---

## Core Services

### 1. PlayerPersonaService

**File:** `src/game_cycle/services/player_persona_service.py`

```python
class PlayerPersonaService:
    """Manages player persona generation, persistence, and updates."""

    def generate_persona(self, player_id: int, age: int, overall: int,
                         position: str) -> PlayerPersona:
        """Generate a persona for a new player with weighted distribution."""
        # Distribution weights (adjusted by age/performance)
        # Base: MONEY_FIRST=25%, COMPETITOR=20%, SYSTEM_FIT=15%,
        #       RING_CHASER=12%, LEGACY_BUILDER=10%, HOMETOWN_HERO=8%,
        #       BIG_MARKET=5%, SMALL_MARKET=5%
        pass

    def get_persona(self, dynasty_id: str, player_id: int) -> PlayerPersona:
        """Load persona from database."""
        pass

    def update_career_context(self, dynasty_id: str, player_id: int,
                              earnings_added: int = 0,
                              won_championship: bool = False,
                              made_pro_bowl: bool = False):
        """Update career earnings, championships, pro bowls."""
        pass

    def get_display_hints(self, persona: PlayerPersona,
                          is_own_team: bool) -> List[str]:
        """Get UI-friendly hints about player preferences."""
        # Own team: "Ring Chaser - Prioritizes winning"
        # Other team: "Values winning over money"
        pass
```

**Persona Generation Logic:**
- Veterans (30+): +15% chance Ring Chaser
- High earners ($50M+ career): -10% Money First, +10% Ring Chaser
- 0 championships + age 28+: +20% Ring Chaser
- High overall (85+): +10% Big Market (endorsement potential)

### 2. TeamAttractivenessService

**File:** `src/game_cycle/services/team_attractiveness_service.py`

```python
class TeamAttractivenessService:
    """Calculates team attractiveness for player decisions."""

    def get_team_attractiveness(self, dynasty_id: str, team_id: int,
                                 season: int) -> TeamAttractiveness:
        """Get full attractiveness data for a team."""
        pass

    def calculate_contender_score(self, dynasty_id: str, team_id: int) -> int:
        """Calculate 0-100 contender score from 5-year history."""
        # Weights: Current record (40%), Playoff appearances (30%),
        #          Super Bowls (20%), Win trajectory (10%)
        pass

    def record_season_result(self, dynasty_id: str, team_id: int,
                             season: int, wins: int, losses: int,
                             made_playoffs: bool, playoff_round: str,
                             won_super_bowl: bool):
        """Record end-of-season results for history tracking."""
        pass

    def update_all_teams(self, dynasty_id: str, season: int):
        """Refresh attractiveness data for all 32 teams."""
        pass
```

### 3. PlayerPreferenceEngine

**File:** `src/player_management/preference_engine.py`

```python
class PlayerPreferenceEngine:
    """Evaluates team offers based on player preferences."""

    def calculate_team_score(self, persona: PlayerPersona,
                             team: TeamAttractiveness,
                             offer: ContractOffer,
                             role: str,  # 'starter', 'backup', 'rotational'
                             is_current_team: bool,
                             is_drafting_team: bool) -> float:
        """Calculate 0-100 attractiveness score for this team/offer combo."""

        # Weighted sum of factors:
        # - Money score (offer vs market max)
        # - Winning score (contender status)
        # - Location score (weather, taxes, proximity to home)
        # - Playing time score (role fit)
        # - Loyalty score (current/drafting team bonus)
        # - Market score (market size preference)
        # - Coaching score (scheme fit) - simplified for now
        # - Relationship score (former teammates) - future
        pass

    def calculate_acceptance_probability(self, persona: PlayerPersona,
                                         team_score: float,
                                         offer_vs_max: float) -> float:
        """Calculate probability player accepts this offer.

        Money Override Rule:
        - offer >= 120% market: 95% acceptance regardless of preferences
        - offer >= 110% market: +30% acceptance bonus
        - offer < 80% market: -40% acceptance penalty
        """
        pass

    def evaluate_all_offers(self, persona: PlayerPersona,
                            offers: List[Tuple[TeamAttractiveness, ContractOffer]]
                           ) -> List[Tuple[int, float, float]]:
        """Rank all offers by preference, return (team_id, score, probability)."""
        pass

    def get_concerns(self, persona: PlayerPersona,
                     team: TeamAttractiveness) -> List[str]:
        """Get list of player concerns about this team."""
        # "Concerned about team's recent playoff history"
        # "Prefers a larger market for endorsements"
        # "May want more guaranteed playing time"
        pass
```

**Scoring Formulas:**

```python
# Money Score (0-100)
money_score = min(100, (offer_aav / market_max_aav) * 100)

# Winning Score (0-100)
winning_score = team.contender_score

# Location Score (0-100)
tax_bonus = (0.13 - team.state_income_tax_rate) / 0.13 * 30  # 0-30 points
weather_bonus = team.weather_score * 0.3  # 0-30 points
home_bonus = 40 if team.state == persona.birthplace_state else 0
location_score = min(100, tax_bonus + weather_bonus + home_bonus)

# Playing Time Score (0-100)
role_scores = {'starter': 100, 'rotational': 60, 'backup': 30}
playing_time_score = role_scores.get(role, 50)

# Loyalty Score (0-100)
loyalty_score = 0
if is_current_team:
    loyalty_score += 50
if is_drafting_team:
    loyalty_score += 50

# Final weighted score
weights = {
    'money': persona.money_importance / 100,
    'winning': persona.winning_importance / 100,
    'location': persona.location_importance / 100,
    'playing_time': persona.playing_time_importance / 100,
    'loyalty': persona.loyalty_importance / 100,
    'market': persona.market_size_importance / 100,
}
total_weight = sum(weights.values())
normalized_weights = {k: v/total_weight for k, v in weights.items()}

final_score = (
    normalized_weights['money'] * money_score +
    normalized_weights['winning'] * winning_score +
    normalized_weights['location'] * location_score +
    normalized_weights['playing_time'] * playing_time_score +
    normalized_weights['loyalty'] * loyalty_score +
    normalized_weights['market'] * market_score
)
```

**Persona-Specific Bonuses:**

| Persona | Bonus Applied |
|---------|---------------|
| RING_CHASER | +20 to winning_score if contender_score > 70 |
| HOMETOWN_HERO | +30 to location_score if in home state |
| MONEY_FIRST | money_importance always treated as 90+ |
| BIG_MARKET | +25 to market_score if market_size > 70 |
| SMALL_MARKET | +25 to market_score if market_size < 40 |
| LEGACY_BUILDER | +40 to loyalty_score for drafting team |
| COMPETITOR | +30 to playing_time_score; -30 if role='backup' |
| SYSTEM_FIT | +20 to coaching_score if scheme matches |

**Money Override Rule:**

```python
def calculate_acceptance_probability(persona, team_score, offer_vs_max):
    base_prob = team_score / 100  # 0.0 - 1.0

    # Money Override
    if offer_vs_max >= 1.20:  # 120%+ of market
        return 0.95  # Almost always accept
    elif offer_vs_max >= 1.10:
        base_prob += 0.30
    elif offer_vs_max < 0.80:
        base_prob -= 0.40

    return max(0.05, min(0.95, base_prob))
```

---

## Service Integrations

### 1. FreeAgencyService Modifications

**File:** `src/game_cycle/services/free_agency_service.py`

```python
# Add to sign_free_agent() method:

def sign_free_agent(self, dynasty_id: str, player_id: int, team_id: int,
                    contract: ContractOffer) -> SigningResult:
    """Sign a free agent with player preference check."""

    # NEW: Get player persona and evaluate acceptance
    persona = self.persona_service.get_persona(dynasty_id, player_id)
    team_attractiveness = self.attractiveness_service.get_team_attractiveness(
        dynasty_id, team_id, self.current_season
    )

    team_score = self.preference_engine.calculate_team_score(
        persona, team_attractiveness, contract,
        role=self._estimate_role(team_id, player_id),
        is_current_team=False,
        is_drafting_team=(team_id == persona.drafting_team_id)
    )

    acceptance_prob = self.preference_engine.calculate_acceptance_probability(
        persona, team_score, contract.aav / market_max_aav
    )

    # Roll the dice
    if random.random() > acceptance_prob:
        concerns = self.preference_engine.get_concerns(persona, team_attractiveness)
        return SigningResult(
            success=False,
            reason="Player declined offer",
            concerns=concerns,
            acceptance_probability=acceptance_prob
        )

    # Proceed with signing...
    return SigningResult(success=True, ...)

def evaluate_player_interest(self, dynasty_id: str, player_id: int,
                             team_id: int) -> InterestResult:
    """Check player's interest level in a team before making offer."""
    # Returns: interest_level (0-100), concerns list, suggested_premium
    pass
```

### 2. ResigningService Modifications

**File:** `src/game_cycle/services/resigning_service.py`

```python
def calculate_contract_adjustment(self, dynasty_id: str, player_id: int,
                                   team_id: int) -> ContractAdjustment:
    """Calculate hometown discount or premium for contract extension."""

    persona = self.persona_service.get_persona(dynasty_id, player_id)
    team = self.attractiveness_service.get_team_attractiveness(...)

    adjustment = 0.0  # Percentage adjustment to market value
    reasons = []

    if persona.persona_type == PersonaType.HOMETOWN_HERO:
        if team.state == persona.birthplace_state:
            adjustment -= 0.15  # 15% discount
            reasons.append("Hometown discount")

    if persona.persona_type == PersonaType.LEGACY_BUILDER:
        if team_id == persona.drafting_team_id:
            adjustment -= 0.12  # 12% discount
            reasons.append("Loyalty to franchise")

    if persona.persona_type == PersonaType.RING_CHASER:
        if team.contender_score > 75:
            adjustment -= 0.10  # 10% discount
            reasons.append("Wants to win championship")

    if persona.persona_type == PersonaType.MONEY_FIRST:
        adjustment += 0.05  # 5% premium
        reasons.append("Expects top dollar")

    return ContractAdjustment(
        percentage=adjustment,
        reasons=reasons,
        persona_hint=self.persona_service.get_display_hints(persona, is_own_team=True)
    )
```

### 3. Trade Veto Integration

**File:** `src/transactions/trade_evaluator.py`

```python
def evaluate_player_trade_acceptance(self, dynasty_id: str, player_id: int,
                                      from_team_id: int,
                                      to_team_id: int) -> TradeAcceptance:
    """Check if player would accept/veto this trade destination."""

    persona = self.persona_service.get_persona(dynasty_id, player_id)
    to_team = self.attractiveness_service.get_team_attractiveness(...)
    from_team = self.attractiveness_service.get_team_attractiveness(...)

    # Legacy builders almost never want to leave
    if persona.persona_type == PersonaType.LEGACY_BUILDER:
        if from_team_id == persona.drafting_team_id:
            return TradeAcceptance(
                would_accept=False,
                acceptance_probability=0.15,
                reason="Wants to remain with franchise"
            )

    # Ring chasers happy to go to contenders
    if persona.persona_type == PersonaType.RING_CHASER:
        if to_team.contender_score > from_team.contender_score + 20:
            return TradeAcceptance(
                would_accept=True,
                acceptance_probability=0.90,
                reason="Excited about contender destination"
            )

    # General evaluation
    to_score = self.preference_engine.calculate_team_score(...)
    from_score = self.preference_engine.calculate_team_score(...)

    # Player accepts if destination scores higher
    would_accept = to_score >= from_score - 10  # 10-point grace

    return TradeAcceptance(
        would_accept=would_accept,
        acceptance_probability=...,
        reason=...
    )
```

---

## UI Integration

### Visibility Rules

**Own Team Players (Full Details):**
```
Persona: Ring Chaser
Priorities: Winning (85), Playing Time (70), Money (50)
Contract Notes: May take discount for contenders
```

**Other Team Players (Hints Only):**
```
"Values winning over money"
"Prefers larger markets"
"Loyal to current team"
```

### Free Agency View Updates

**File:** `game_cycle_ui/views/free_agency_view.py`

- Add "Interest Level" indicator (Low/Medium/High) for each FA
- Show concerns when hovering over low-interest players
- Display acceptance probability after making offer
- Show "Player Declined" with reasons if rejected

### Signing Dialog Updates

- Show player's key preferences before offering
- Display estimated acceptance probability
- Suggest premium needed to secure player
- Show competing offers' attractiveness (if bidding war)

---

## Tollgates

### Tollgate 1: Core Data Models ✅ COMPLETE
**Files:**
- `src/player_management/__init__.py` (NEW)
- `src/player_management/player_persona.py` (NEW)
- `src/player_management/team_attractiveness.py` (NEW)
- `src/game_cycle/database/schema.sql` (ADD tables)

**Deliverables:**
- PersonaType enum with 8 archetypes
- PlayerPersona dataclass with validation
- TeamAttractiveness dataclass
- Database tables with indexes
- Unit tests (10+)

**Acceptance Criteria:**
- [x] All enums and dataclasses validate correctly
- [x] DB tables created with dynasty isolation
- [x] to_dict/from_dict serialization works

**Tests:** 71 passing
- `tests/game_cycle/models/test_player_persona.py` (24 tests)
- `tests/game_cycle/models/test_team_attractiveness.py` (31 tests)
- `tests/game_cycle/database/test_persona_schema.py` (16 tests)

---

### Tollgate 2: Static Team Data ✅ COMPLETE
**Files:**
- `src/config/team_attractiveness_static.json` (NEW)

**Deliverables:**
- Market size for all 32 teams (1-100)
- State income tax rates
- Weather scores
- Metro population data

**Acceptance Criteria:**
- [x] All 32 teams have complete data
- [x] No-tax states correctly identified (8 teams: MIA, JAX, TB, HOU, DAL, TEN, LV, SEA)
- [x] Data validated against real-world sources

**Tests:** 11 passing
- `tests/config/test_team_attractiveness_config.py`

---

### Tollgate 3: Persona Service ✅ COMPLETE
**Files:**
- `src/game_cycle/services/player_persona_service.py` (NEW)
- `src/game_cycle/database/persona_api.py` (NEW)

**Deliverables:**
- Persona generation with weighted distribution
- Age/performance modifiers
- CRUD operations for personas
- Display hint generation
- Integration tests (8+)

**Acceptance Criteria:**
- [x] Distribution matches expected weights (MONEY_FIRST=25%, COMPETITOR=20%, etc.)
- [x] Veterans (30+) skew toward Ring Chaser (+15%)
- [x] Personas persist across sessions (database)
- [x] Own team vs other team hints differ

**Tests:** 18 passing
- `tests/game_cycle/services/test_player_persona_service.py`

---

### Tollgate 4: Team Attractiveness Service ✅ COMPLETE
**Files:**
- `src/game_cycle/services/team_attractiveness_service.py` (NEW)
- `src/game_cycle/database/team_history_api.py` (NEW)

**Deliverables:**
- [x] 5-year history tracking via TeamHistoryAPI
- [x] Contender score calculation (weighted formula)
- [x] Season result recording from standings/playoff tables
- [x] Winning culture score from 5-year average
- [x] Static + dynamic data merge for TeamAttractiveness

**Acceptance Criteria:**
- [x] History table populated after each season ends
- [x] Contender scores update correctly based on 5-year window
- [x] 5-year window respected (oldest season dropped when 6th added)
- [x] Integration tests (18+)

**Contender Score Algorithm:**
```python
contender_score = (
    current_record_score * 0.40 +  # Current season win %
    playoff_score * 0.30 +         # Playoff appearances (0-5)
    super_bowl_score * 0.20 +      # Super Bowl wins (max 100 at 2+)
    culture_score * 0.10           # 5-year average win %
)
```

**Tests:** 18 passing
- `tests/game_cycle/services/test_team_attractiveness_service.py`
  - TestTeamHistoryAPI (4 tests) - CRUD, dynasty isolation
  - TestContenderScore (4 tests) - Score calculation scenarios
  - TestSeasonRecording (3 tests) - Standings/playoffs integration
  - TestAttractivenessObject (3 tests) - Static + dynamic merge
  - TestAttractivenessTable (2 tests) - Database persistence
  - TestWinningCulture (2 tests) - Culture score calculation

**Schema Update:** Updated `standings` table in `schema.sql` to include `dynasty_id` and `season` columns for proper dynasty isolation (migration added to `connection.py`).

---

### Tollgate 5: Preference Engine ✅ COMPLETE
**Files:**
- `src/player_management/preference_engine.py` (NEW)

**Deliverables:**
- [x] ContractOffer dataclass with `offer_vs_market` and `guaranteed_percentage` properties
- [x] OfferEvaluation dataclass for evaluation results
- [x] PlayerPreferenceEngine class with 6-factor weighted scoring
- [x] Team scoring algorithm (money, winning, location, playing_time, loyalty, market)
- [x] Acceptance probability calculation with money override
- [x] Persona-specific bonuses for all 8 persona types
- [x] Concern generation based on persona and team attributes
- [x] Unit tests (41 tests)

**Acceptance Criteria:**
- [x] Ring Chaser prefers contenders (+20 bonus if contender_score > 70)
- [x] Money First takes highest offer (money_score +10 bonus, 85%+ acceptance at market)
- [x] Money override works at 120%+ (95% acceptance regardless of preferences)
- [x] Concerns accurately reflect persona/team mismatches
- [x] Weighted score normalizes preferences correctly

**Key Methods:**
```python
class PlayerPreferenceEngine:
    def calculate_team_score(persona, team, offer, is_current_team, is_drafting_team) -> int
    def calculate_acceptance_probability(persona, team_score, offer_vs_market) -> float
    def get_concerns(persona, team, offer) -> List[str]
    def evaluate_all_offers(persona, offers, current_team_id) -> List[OfferEvaluation]
    def should_accept_offer(persona, team, offer, is_current_team, is_drafting_team) -> Tuple[bool, float, List[str]]
```

**Tests:** 41 passing
- `tests/player_management/test_preference_engine.py`
  - TestContractOffer (5 tests) - offer_vs_market ratio, guaranteed percentage
  - TestMoneyScore (5 tests) - score calculation at various market ratios
  - TestWinningScore (2 tests) - contender score mapping
  - TestLocationScore (3 tests) - tax, weather, home state bonuses
  - TestPlayingTimeScore (3 tests) - starter/rotational/backup roles
  - TestPersonaBonuses (5 tests) - all 8 persona bonus types
  - TestWeightedScore (3 tests) - persona-weighted final scores
  - TestAcceptanceProbability (6 tests) - money override, bonuses, penalties
  - TestConcerns (5 tests) - concern generation scenarios
  - TestOfferEvaluation (2 tests) - ranking and evaluation
  - TestShouldAccept (2 tests) - acceptance decision flow

---

### Tollgate 6: Free Agency Integration ✅ COMPLETE
**Files:**
- `src/game_cycle/services/free_agency_service.py` (MODIFIED)
- `tests/game_cycle/services/test_free_agency_player_preferences.py` (NEW)

**Deliverables:**
- [x] Lazy-loaded service getters (`_get_persona_service()`, `_get_attractiveness_service()`, `_get_preference_engine()`)
- [x] Helper methods (`_calculate_age()`, `_estimate_role()`)
- [x] `_check_player_acceptance()` - Evaluates if player accepts offer based on persona
- [x] Modified `sign_free_agent()` - Adds `skip_preference_check` parameter, returns rejection info
- [x] `evaluate_player_interest()` - Pre-signing interest check for UI (interest_level, concerns, suggested_premium)
- [x] Modified `process_ai_signings()` - Handles rejections, tracks in `rejections` list

**Acceptance Criteria:**
- [x] Players can reject offers based on preferences
- [x] Rejection reasons (concerns) returned to caller
- [x] AI teams evaluate player interest before offering
- [x] AI teams handle rejections and try other players
- [x] Integration tests (18 tests)

**Key Implementation Details:**
- Database connection mismatch solved via lazy-loading (FreeAgencyService uses db_path, TeamAttractivenessService requires GameCycleDatabase)
- Graceful degradation: If preference system fails, signing proceeds
- Persona generated on-demand if missing
- Interest levels: "high" (≥75%), "medium" (45-74%), "low" (<45%)
- Suggested premium: 1.0 (high), 1.10 (medium), 1.20 (low interest)

**Tests:** 18 passing
- `tests/game_cycle/services/test_free_agency_player_preferences.py`
  - TestPreferenceIntegration (5 tests)
  - TestConcernGeneration (3 tests)
  - TestOfferEvaluation (1 test)
  - TestShouldAcceptOffer (2 tests)
  - TestInterestLevelCalculation (3 tests)
  - TestContractOfferProperties (4 tests)

---

### Tollgate 7: Re-signing Integration ✅ COMPLETE
**Files:**
- `src/game_cycle/services/resigning_service.py` (MODIFIED)
- `tests/game_cycle/services/test_resigning_player_preferences.py` (NEW)

**Deliverables:**
- [x] Lazy-loaded service getters (same pattern as FreeAgencyService)
- [x] Helper methods (`_calculate_age()`, `_estimate_role()`)
- [x] `_check_player_acceptance()` - Evaluates if player accepts with `is_current_team=True` for loyalty bonus
- [x] Modified `resign_player()` - Adds `skip_preference_check` parameter, returns rejection info
- [x] Updated `_should_ai_resign()` - Returns `Tuple[bool, float, List[str]]` (should_attempt, probability, concerns)
- [x] Modified `process_ai_resignings()` - Handles rejections, tracks in `rejections` list

**Acceptance Criteria:**
- [x] Players use persona to accept/reject re-signing offers
- [x] Loyalty bonus applied for current team (`is_current_team=True` gives +50)
- [x] LEGACY_BUILDER gets additional +40 loyalty bonus
- [x] AI teams evaluate player preferences before attempting re-signing
- [x] Rejections handled gracefully (player released to FA)
- [x] Integration tests (8 tests)

**Key Difference from Free Agency:**
| Aspect | Free Agency | Re-signing |
|--------|-------------|------------|
| `is_current_team` | `False` | `True` |
| Loyalty bonus | None | +50 points |
| LEGACY_BUILDER | No special handling | +40 additional loyalty |

**Tests:** 8 passing
- `tests/game_cycle/services/test_resigning_player_preferences.py`
  - TestResigningWithPreferences (3 tests) - Current team bonus, acceptance, rejection
  - TestLoyaltyBonus (2 tests) - Legacy Builder loyalty, high acceptance
  - TestAIResigningWithPreferences (2 tests) - AI evaluation, concerns
  - TestResigningVsFreAgencyDifference (1 test) - Same offer comparison

---

### Tollgate 8: Trade Veto & UI
**Files:**
- `src/transactions/trade_evaluator.py` (MODIFY)
- `game_cycle_ui/views/free_agency_view.py` (MODIFY)
- `game_cycle_ui/dialogs/signing_dialog.py` (NEW or MODIFY)

**Deliverables:**
- Trade destination evaluation
- Legacy builder veto logic
- UI interest indicators
- Signing dialog with preferences
- End-to-end tests

**Acceptance Criteria:**
- Trade vetoes work correctly
- UI shows appropriate hints
- Full user flow tested

---

## Critical Files Summary

### New Files
| File | Purpose |
|------|---------|
| `src/player_management/__init__.py` | Package init |
| `src/player_management/player_persona.py` | PlayerPersona dataclass, PersonaType enum |
| `src/player_management/team_attractiveness.py` | TeamAttractiveness dataclass |
| `src/player_management/preference_engine.py` | Scoring and acceptance logic |
| `src/game_cycle/services/player_persona_service.py` | Persona CRUD and generation |
| `src/game_cycle/services/team_attractiveness_service.py` | Team history and scoring |
| `src/game_cycle/database/persona_api.py` | Database operations for personas |
| `src/game_cycle/database/team_history_api.py` | Database operations for history |
| `src/config/team_attractiveness_static.json` | Static team market data |

### Modified Files
| File | Changes |
|------|---------|
| `src/game_cycle/database/schema.sql` | Add 3 new tables |
| `src/game_cycle/services/free_agency_service.py` | Add player acceptance logic |
| `src/game_cycle/services/resigning_service.py` | Add contract adjustments |
| `src/transactions/trade_evaluator.py` | Add trade veto logic |
| `src/game_cycle/handlers/offseason.py` | Record season history |
| `game_cycle_ui/views/free_agency_view.py` | Add interest indicators |

### Reference Files (Read-Only)
| File | Pattern to Follow |
|------|-------------------|
| `src/team_management/gm_archetype.py` | Archetype dataclass pattern |
| `src/transactions/personality_modifiers.py` | Modifier calculation pattern |
| `src/transactions/transaction_constants.py` | Enum and constants pattern |

---

## Testing Strategy

### Unit Tests
- Persona generation distribution (100+ generations, check percentages)
- Team scoring calculations (known inputs → expected outputs)
- Money override thresholds (boundary testing)
- Persona bonus application

### Integration Tests
- Free agent signing with rejection
- Re-signing with discount calculation
- Trade veto by Legacy Builder
- Season history accumulation

### End-to-End Tests
- Complete FA signing flow with UI
- Multi-season history tracking
- Persona evolution (earnings updates)

---

## Future Considerations (Out of Scope)

- Draft Day preferences (Eli Manning scenario) - Milestone #7+
- Relationship tracking (former teammates) - requires player history
- Scheme fit details - requires coaching system (#20)
- Social media integration (#13)