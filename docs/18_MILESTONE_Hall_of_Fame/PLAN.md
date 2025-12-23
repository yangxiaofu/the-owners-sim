# Milestone 18: Hall of Fame

## Overview

Annual Hall of Fame voting for retired players, with realistic criteria based on career accomplishments, awards, and statistical achievements. Creates legacy moments that connect past and present.

**Status**: In Progress (T1-T5 Complete)
**Dependencies**: Player Retirements (✅), Awards System (✅), Statistics (✅)
**Estimated Effort**: Medium (8 tollgates)

### Tollgate Status
| Tollgate | Status | Tests |
|----------|--------|-------|
| **T1** Database Schema | ✅ Complete | 16 tests |
| **T2** Eligibility Service | ✅ Complete | 22 tests |
| **T3** HOF Scoring Engine | ✅ Complete | 56 tests |
| **T4** Voting Engine | ✅ Complete | 39 tests |
| **T5** Induction Service | ✅ Complete | 51 tests |
| **T6** Database API | ✅ (Merged into T1) | - |
| **T7** OFFSEASON_HONORS Integration | ⏳ Not Started | - |
| **T8** UI Implementation | ⏳ Not Started | - |

---

## Design Philosophy

1. **Realistic Voting** - HOF induction is rare and meaningful (~5 per year max)
2. **Multi-Factor Scoring** - Awards, stats, championships, longevity all matter
3. **First-Ballot Recognition** - Elite players inducted immediately
4. **Patient Waiting** - Good players may wait years or never get in
5. **Dynasty Pride** - Fans celebrate when their team's legends are enshrined

---

## Tollgate Summary

| Tollgate | Description | Key Deliverables |
|----------|-------------|------------------|
| **T1** | Database Schema | `hall_of_fame`, `hof_voting_history` tables |
| **T2** | Eligibility Service | 5-year wait, career minimums, eligible candidates |
| **T3** | HOF Scoring Engine | Factor weights, position thresholds, score calculation |
| **T4** | Voting Engine | Simulated voting, max 5 inductees, multi-year tracking |
| **T5** | Induction Service | Induction records, speech generation, ceremony data |
| **T6** | Database API | HOFAPI with full CRUD operations |
| **T7** | OFFSEASON_HONORS Integration | HOF voting in honors stage, headlines |
| **T8** | UI Implementation | HOF View, Induction Dialog, Team History integration |

---

## Tollgate 1: Database Schema

**Goal**: Create database tables to store Hall of Fame data.

### Schema Design

```sql
-- Hall of Fame members
CREATE TABLE IF NOT EXISTS hall_of_fame (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    player_id TEXT NOT NULL,

    -- Induction details
    induction_year INTEGER NOT NULL,           -- Season inducted
    years_eligible INTEGER NOT NULL,           -- Years on ballot before induction
    is_first_ballot INTEGER NOT NULL DEFAULT 0, -- First-ballot inductee

    -- Career summary (denormalized for display)
    player_name TEXT NOT NULL,
    primary_position TEXT NOT NULL,
    career_seasons INTEGER NOT NULL,
    teams_played_for TEXT NOT NULL,            -- JSON array of team names

    -- Career achievements
    championships INTEGER NOT NULL DEFAULT 0,
    mvp_awards INTEGER NOT NULL DEFAULT 0,
    all_pro_first_team INTEGER NOT NULL DEFAULT 0,
    all_pro_second_team INTEGER NOT NULL DEFAULT 0,
    pro_bowl_selections INTEGER NOT NULL DEFAULT 0,

    -- Key career stats (position-specific)
    career_stats TEXT NOT NULL,                -- JSON with position stats

    -- HOF score that led to induction
    hof_score REAL NOT NULL,

    -- Ceremony details
    speech_highlights TEXT,                    -- Generated speech excerpts
    presenter_name TEXT,                       -- Who presented them

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(dynasty_id, player_id)
);

-- Voting history for all candidates
CREATE TABLE IF NOT EXISTS hof_voting_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    voting_year INTEGER NOT NULL,              -- Season of voting
    player_id TEXT NOT NULL,

    -- Candidate info
    player_name TEXT NOT NULL,
    primary_position TEXT NOT NULL,
    retirement_year INTEGER NOT NULL,
    years_on_ballot INTEGER NOT NULL,          -- How many years they've been eligible

    -- Voting results
    vote_percentage REAL NOT NULL,             -- 0.0-1.0
    votes_received INTEGER NOT NULL,
    votes_needed INTEGER NOT NULL,

    -- Outcome
    was_inducted INTEGER NOT NULL DEFAULT 0,
    is_first_ballot INTEGER NOT NULL DEFAULT 0,

    -- Scoring breakdown
    hof_score REAL NOT NULL,
    score_breakdown TEXT NOT NULL,             -- JSON with factor contributions

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(dynasty_id, voting_year, player_id)
);

-- Indices for common queries
CREATE INDEX IF NOT EXISTS idx_hof_dynasty ON hall_of_fame(dynasty_id);
CREATE INDEX IF NOT EXISTS idx_hof_induction_year ON hall_of_fame(dynasty_id, induction_year);
CREATE INDEX IF NOT EXISTS idx_hof_voting_dynasty_year ON hof_voting_history(dynasty_id, voting_year);
CREATE INDEX IF NOT EXISTS idx_hof_voting_player ON hof_voting_history(dynasty_id, player_id);
```

### Acceptance Criteria
- [ ] Schema added to `full_schema.sql`
- [ ] Tables created on dynasty initialization
- [ ] Indices support efficient lookups

---

## Tollgate 2: HOF Eligibility Service

**Goal**: Determine which retired players are eligible for HOF voting each year.

### File: `src/game_cycle/services/hof_eligibility_service.py`

```python
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class EligibilityStatus(Enum):
    ELIGIBLE = "ELIGIBLE"
    TOO_RECENT = "TOO_RECENT"      # Retired < 5 seasons ago
    BELOW_MINIMUM = "BELOW_MINIMUM" # Career too short
    ALREADY_INDUCTED = "ALREADY_INDUCTED"
    REMOVED_FROM_BALLOT = "REMOVED_FROM_BALLOT"  # 20 years without induction

@dataclass
class HOFCandidate:
    """A player eligible for HOF consideration."""
    player_id: str
    player_name: str
    primary_position: str
    retirement_year: int
    years_on_ballot: int
    career_seasons: int
    teams_played_for: List[str]

    # Career achievements
    championships: int
    mvp_awards: int
    all_pro_first_team: int
    all_pro_second_team: int
    pro_bowl_selections: int

    # Key stats
    career_stats: dict

    # Pre-computed HOF score
    hof_score: float
    eligibility_status: EligibilityStatus

class HOFEligibilityService:
    """
    Determines HOF eligibility for retired players.

    Eligibility Rules:
    - Must be retired for 5+ complete seasons
    - Must meet career minimum thresholds (position-specific)
    - Removed from ballot after 20 years without induction
    - Not already inducted
    """

    # Minimum career requirements by position
    CAREER_MINIMUMS = {
        "QB": {"seasons": 8, "games": 80, "passing_yards": 15000},
        "RB": {"seasons": 6, "games": 60, "rushing_yards": 4000},
        "WR": {"seasons": 6, "games": 60, "receiving_yards": 5000},
        "TE": {"seasons": 6, "games": 60, "receiving_yards": 3000},
        "OL": {"seasons": 8, "games": 100},  # OT, OG, C
        "DL": {"seasons": 8, "games": 80, "sacks": 30},  # DE, DT
        "LB": {"seasons": 8, "games": 80, "tackles": 400},
        "DB": {"seasons": 8, "games": 80, "interceptions": 15},  # CB, FS, SS
        "K": {"seasons": 10, "games": 100, "field_goals": 150},
        "P": {"seasons": 10, "games": 100},
    }

    WAITING_PERIOD = 5  # Years after retirement before eligible
    MAX_BALLOT_YEARS = 20  # Removed from ballot after this

    def get_eligible_candidates(
        self,
        dynasty_id: str,
        current_season: int
    ) -> List[HOFCandidate]:
        """Get all players eligible for HOF voting this year."""
        ...

    def check_eligibility(
        self,
        player_id: str,
        retirement_year: int,
        current_season: int,
        career_stats: dict,
        position: str
    ) -> EligibilityStatus:
        """Check if a specific player is eligible."""
        ...

    def _meets_career_minimums(
        self,
        position: str,
        career_stats: dict
    ) -> bool:
        """Check if player meets minimum career thresholds."""
        ...
```

### Position Group Mapping
```python
POSITION_GROUPS = {
    "QB": "QB",
    "RB": "RB", "FB": "RB",
    "WR": "WR",
    "TE": "TE",
    "LT": "OL", "LG": "OL", "C": "OL", "RG": "OL", "RT": "OL",
    "LE": "DL", "DT": "DL", "RE": "DL", "EDGE": "DL",
    "LOLB": "LB", "MLB": "LB", "ROLB": "LB",
    "CB": "DB", "FS": "DB", "SS": "DB",
    "K": "K",
    "P": "P",
}
```

### Acceptance Criteria
- [ ] Service correctly identifies eligible candidates
- [ ] 5-year waiting period enforced
- [ ] Career minimums checked by position
- [ ] 20-year ballot limit enforced
- [ ] Already-inducted players excluded

---

## Tollgate 3: HOF Scoring Engine

**Goal**: Calculate HOF scores based on career accomplishments.

### File: `src/game_cycle/services/hof_scoring_engine.py`

```python
from dataclasses import dataclass
from typing import Dict, List, Tuple
from enum import Enum

class HOFTier(Enum):
    """Classification of HOF candidacy strength."""
    FIRST_BALLOT = "FIRST_BALLOT"      # 85+ score - Immediate lock
    STRONG = "STRONG"                   # 70-84 - Likely eventual inductee
    BORDERLINE = "BORDERLINE"           # 55-69 - May get in eventually
    LONG_SHOT = "LONG_SHOT"             # 40-54 - Unlikely but possible
    NOT_HOF = "NOT_HOF"                 # <40 - Won't make it

@dataclass
class HOFScoreBreakdown:
    """Detailed breakdown of HOF score calculation."""
    total_score: float
    tier: HOFTier

    # Factor contributions
    awards_score: float          # MVP, All-Pro, Pro Bowl
    championships_score: float   # Super Bowl wins
    stats_score: float           # Career stats vs. position averages
    longevity_score: float       # Career length and consistency
    peak_score: float            # Best seasons (peak performance)

    # Bonus/penalty
    first_ballot_bonus: float    # Extra points for dominant careers
    position_scarcity: float     # Harder positions get small boost

    # Individual factors for display
    factor_details: Dict[str, float]

class HOFScoringEngine:
    """
    Calculates Hall of Fame scores for candidates.

    Scoring Philosophy:
    - Awards are most important (MVP = huge boost)
    - Stats matter but context-dependent
    - Championships provide meaningful boost
    - Longevity shows sustained excellence
    - Peak performance distinguishes greats

    Score Ranges:
    - 85-100: First-ballot lock (rare, ~1-2 per year)
    - 70-84: Strong candidate (likely inducted within 5 years)
    - 55-69: Borderline (may wait 10+ years or never)
    - 40-54: Long shot (needs weak class to have chance)
    - 0-39: Not HOF caliber
    """

    # Factor weights (must sum to 100)
    FACTOR_WEIGHTS = {
        "awards": 30,
        "championships": 15,
        "stats": 25,
        "longevity": 15,
        "peak": 15,
    }

    # Award point values (within awards factor)
    AWARD_VALUES = {
        "mvp": 25,              # MVP is huge
        "all_pro_first": 8,     # First-team All-Pro
        "all_pro_second": 4,    # Second-team All-Pro
        "pro_bowl": 2,          # Pro Bowl selection
        "opoy": 15,             # Offensive Player of Year
        "dpoy": 15,             # Defensive Player of Year
        "oroy": 5,              # Offensive Rookie of Year
        "droy": 5,              # Defensive Rookie of Year
        "cpoy": 8,              # Comeback Player of Year
    }

    # Championship values
    CHAMPIONSHIP_VALUES = {
        "super_bowl_win": 12,
        "super_bowl_mvp": 8,
        "conference_championship": 3,
    }

    # Position-specific stat thresholds for "elite" status
    ELITE_STAT_THRESHOLDS = {
        "QB": {
            "passing_yards": 50000,
            "passing_tds": 350,
            "passer_rating": 95.0,
        },
        "RB": {
            "rushing_yards": 12000,
            "rushing_tds": 80,
            "total_yards": 15000,
        },
        "WR": {
            "receiving_yards": 12000,
            "receptions": 800,
            "receiving_tds": 70,
        },
        "TE": {
            "receiving_yards": 8000,
            "receptions": 600,
            "receiving_tds": 50,
        },
        "DL": {
            "sacks": 100,
            "tackles_for_loss": 100,
        },
        "LB": {
            "tackles": 1200,
            "sacks": 40,
            "interceptions": 15,
        },
        "DB": {
            "interceptions": 50,
            "passes_defended": 120,
        },
    }

    def calculate_score(
        self,
        candidate: "HOFCandidate"
    ) -> HOFScoreBreakdown:
        """Calculate comprehensive HOF score for a candidate."""
        ...

    def _calculate_awards_score(
        self,
        mvp: int,
        all_pro_first: int,
        all_pro_second: int,
        pro_bowl: int,
        other_awards: Dict[str, int]
    ) -> Tuple[float, Dict[str, float]]:
        """Calculate awards contribution to HOF score."""
        ...

    def _calculate_stats_score(
        self,
        position: str,
        career_stats: dict
    ) -> Tuple[float, Dict[str, float]]:
        """Calculate stats contribution vs. position averages."""
        ...

    def _calculate_longevity_score(
        self,
        career_seasons: int,
        games_played: int
    ) -> float:
        """Calculate longevity contribution."""
        # 12+ seasons = max points
        # Bonus for games played (durability)
        ...

    def _calculate_peak_score(
        self,
        best_seasons: List[dict]
    ) -> float:
        """Calculate peak performance contribution."""
        # Look at best 3-5 seasons
        # Elite peaks > sustained good
        ...

    def _determine_tier(self, total_score: float) -> HOFTier:
        """Determine HOF tier based on total score."""
        if total_score >= 85:
            return HOFTier.FIRST_BALLOT
        elif total_score >= 70:
            return HOFTier.STRONG
        elif total_score >= 55:
            return HOFTier.BORDERLINE
        elif total_score >= 40:
            return HOFTier.LONG_SHOT
        else:
            return HOFTier.NOT_HOF
```

### Acceptance Criteria
- [ ] Scoring engine produces realistic scores
- [ ] First-ballot players score 85+
- [ ] Borderline players score 55-69
- [ ] Position-specific thresholds calibrated
- [ ] Score breakdown provides transparency

---

## Tollgate 4: HOF Voting Engine

**Goal**: Simulate annual HOF voting process.

### File: `src/game_cycle/services/hof_voting_engine.py`

```python
from dataclasses import dataclass
from typing import List, Optional, Tuple

@dataclass
class HOFVotingResult:
    """Result of a single candidate's voting."""
    player_id: str
    player_name: str
    position: str
    years_on_ballot: int

    vote_percentage: float
    votes_received: int
    votes_needed: int

    was_inducted: bool
    is_first_ballot: bool

    hof_score: float
    score_breakdown: dict

@dataclass
class HOFVotingSession:
    """Results of annual HOF voting."""
    dynasty_id: str
    voting_year: int

    inductees: List[HOFVotingResult]
    non_inductees: List[HOFVotingResult]
    removed_from_ballot: List[HOFVotingResult]  # 20-year limit reached

    total_candidates: int
    induction_threshold: float  # Usually 0.80 (80%)

class HOFVotingEngine:
    """
    Simulates Hall of Fame voting process.

    Voting Rules:
    - 80% vote threshold required for induction
    - Maximum 5 inductees per year (if >5 qualify, take top 5)
    - First-ballot = inducted in first year of eligibility
    - Candidates with <5% votes removed from ballot
    - 20-year maximum on ballot

    Voting Simulation:
    - Higher HOF scores = higher vote percentages
    - First-ballot locks get 95%+ votes
    - Borderline candidates fluctuate year to year
    - Weak classes = more inductees, strong classes = fewer
    """

    INDUCTION_THRESHOLD = 0.80      # 80% to get in
    MAX_INDUCTEES_PER_YEAR = 5
    MIN_VOTE_TO_STAY = 0.05         # 5% minimum to remain on ballot
    MAX_YEARS_ON_BALLOT = 20

    def conduct_voting(
        self,
        dynasty_id: str,
        voting_year: int,
        candidates: List["HOFCandidate"]
    ) -> HOFVotingSession:
        """
        Conduct annual HOF voting for all eligible candidates.

        Returns complete voting results including inductees and non-inductees.
        """
        ...

    def _simulate_vote_percentage(
        self,
        hof_score: float,
        years_on_ballot: int,
        is_first_ballot: bool,
        class_strength: float
    ) -> float:
        """
        Simulate vote percentage for a candidate.

        Factors:
        - HOF score is primary driver
        - Years on ballot can boost (building support) or hurt (fatigue)
        - Strong classes reduce individual vote shares
        """
        ...

    def _calculate_class_strength(
        self,
        candidates: List["HOFCandidate"]
    ) -> float:
        """
        Calculate how strong the overall class is.

        Strong class = multiple first-ballot candidates = harder for borderline.
        Weak class = fewer top candidates = more room for borderline inductees.
        """
        ...

    def _handle_max_inductee_limit(
        self,
        candidates_above_threshold: List[Tuple[str, float]]
    ) -> List[str]:
        """
        If more than 5 candidates reach 80%, take top 5 by vote %.
        """
        ...
```

### Vote Percentage Simulation

```python
def _simulate_vote_percentage(
    self,
    hof_score: float,
    years_on_ballot: int,
    is_first_ballot: bool,
    class_strength: float
) -> float:
    """
    Convert HOF score to simulated vote percentage.

    Base formula:
    - 85+ score = 90-99% votes (first-ballot lock)
    - 70-84 score = 70-89% votes (strong but may not pass first year)
    - 55-69 score = 40-75% votes (borderline, varies by year)
    - 40-54 score = 10-45% votes (long shot)
    - <40 score = 1-15% votes (filler candidates)

    Modifiers:
    - First-ballot bonus: +5-10%
    - Years on ballot: +1-2% per year (building support) up to year 10
    - Years on ballot: -1% per year after year 15 (voter fatigue)
    - Class strength: -5% for strong class, +5% for weak class
    - Random variance: ±5% to simulate unpredictability
    """
    # Base vote percentage from HOF score
    if hof_score >= 85:
        base_pct = 0.90 + (hof_score - 85) * 0.006  # 90-99%
    elif hof_score >= 70:
        base_pct = 0.70 + (hof_score - 70) * 0.013  # 70-89%
    elif hof_score >= 55:
        base_pct = 0.40 + (hof_score - 55) * 0.023  # 40-75%
    elif hof_score >= 40:
        base_pct = 0.10 + (hof_score - 40) * 0.023  # 10-45%
    else:
        base_pct = 0.01 + (hof_score / 40) * 0.14   # 1-15%

    # Apply modifiers...
    return min(0.99, max(0.01, final_pct))
```

### Acceptance Criteria
- [ ] Voting produces realistic results
- [ ] First-ballot players get 95%+ votes
- [ ] Borderline players fluctuate year-to-year
- [ ] Max 5 inductees per year enforced
- [ ] Ballot removal rules work correctly

---

## Tollgate 5: HOF Induction Service

**Goal**: Handle induction ceremony and record creation.

### File: `src/game_cycle/services/hof_induction_service.py`

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class InductionSpeechHighlights:
    """Generated speech excerpts for induction ceremony."""
    opening: str           # "Thank you to the Hall selection committee..."
    career_reflection: str # "When I was drafted by the Bears..."
    thank_yous: str        # "I want to thank Coach Smith, my teammates..."
    legacy_statement: str  # "I hope I've made this city proud..."
    closing: str           # "God bless you all, and Go Bears!"

@dataclass
class InductionCeremony:
    """Complete induction ceremony data."""
    inductee_id: str
    inductee_name: str
    position: str
    induction_year: int

    # Presenter (former teammate, coach, or family)
    presenter_name: str
    presenter_relationship: str

    # Speech content
    speech_highlights: InductionSpeechHighlights

    # Career summary for display
    career_summary: str
    career_stats: dict
    achievements: List[str]

    # Visual elements
    bust_description: str  # "Bronze bust captures his intense gaze..."
    jacket_moment: str     # "He slipped on the gold jacket..."

class HOFInductionService:
    """
    Handles Hall of Fame induction ceremonies.

    Responsibilities:
    - Create permanent HOF record
    - Generate speech highlights
    - Select presenter
    - Create ceremony narrative
    """

    def create_induction(
        self,
        dynasty_id: str,
        voting_result: "HOFVotingResult",
        candidate: "HOFCandidate"
    ) -> InductionCeremony:
        """Create induction record and ceremony data."""
        ...

    def _generate_speech(
        self,
        player_name: str,
        position: str,
        teams: List[str],
        achievements: List[str],
        career_seasons: int
    ) -> InductionSpeechHighlights:
        """Generate speech excerpts for the inductee."""
        ...

    def _select_presenter(
        self,
        player_id: str,
        teams: List[str],
        career_years: Tuple[int, int]
    ) -> Tuple[str, str]:
        """
        Select presenter for induction ceremony.

        Priorities:
        1. Position coach who developed them
        2. Former teammate (already in HOF preferred)
        3. Head coach from championship team
        4. Family member
        """
        ...

    def _generate_bust_description(
        self,
        player_name: str,
        position: str,
        defining_trait: str
    ) -> str:
        """Generate narrative description of bronze bust."""
        ...
```

### Speech Templates

```python
SPEECH_TEMPLATES = {
    "opening": [
        "Standing here in Canton, I'm overwhelmed with gratitude.",
        "Thirty years ago, I was just a kid with a dream. Today, that dream is complete.",
        "To be mentioned alongside the legends in this hall... it's beyond words.",
    ],
    "career_reflection": [
        "When {team} drafted me, I had no idea where this journey would lead.",
        "I remember my first game like it was yesterday. The nerves, the excitement.",
        "Every snap, every hit, every victory and defeat brought me to this moment.",
    ],
    "thank_yous": [
        "To my teammates who went to war with me every Sunday - this is ours.",
        "To {coach}, who believed in me when others didn't - thank you.",
        "To my family, who sacrificed so I could chase this dream - I love you.",
    ],
    "legacy": [
        "I hope I represented {team} with honor and pride.",
        "If I inspired one kid to never give up, this was all worth it.",
        "Football gave me everything. I hope I gave something back.",
    ],
}
```

### Acceptance Criteria
- [ ] Induction records created in database
- [ ] Speech highlights generated appropriately
- [ ] Presenters selected logically
- [ ] Ceremony data complete for UI display
- [ ] One-day contracts handled (retire with original team)

---

## Tollgate 6: Database API

**Goal**: Create HOFAPI with full database operations.

### File: `src/game_cycle/database/hof_api.py`

```python
from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime

class HOFAPI:
    """
    Database API for Hall of Fame operations.

    All operations are dynasty-isolated.
    """

    def __init__(self, connection, dynasty_id: str):
        self.conn = connection
        self.dynasty_id = dynasty_id

    # ============ HOF Members ============

    def get_all_inductees(
        self,
        position_filter: Optional[str] = None,
        team_filter: Optional[str] = None
    ) -> List[Dict]:
        """Get all Hall of Fame members."""
        ...

    def get_inductee(self, player_id: str) -> Optional[Dict]:
        """Get specific HOF member by player ID."""
        ...

    def get_inductees_by_year(self, induction_year: int) -> List[Dict]:
        """Get all players inducted in a specific year."""
        ...

    def get_team_hof_members(self, team_name: str) -> List[Dict]:
        """Get all HOF members who played for a team."""
        ...

    def add_inductee(
        self,
        player_id: str,
        induction_year: int,
        years_eligible: int,
        is_first_ballot: bool,
        player_data: Dict,
        ceremony_data: Dict
    ) -> int:
        """Add new HOF member."""
        ...

    def get_inductee_count(self) -> int:
        """Get total number of HOF members."""
        ...

    # ============ Voting History ============

    def get_voting_history(
        self,
        voting_year: Optional[int] = None,
        player_id: Optional[str] = None
    ) -> List[Dict]:
        """Get voting history, optionally filtered."""
        ...

    def save_voting_results(
        self,
        voting_year: int,
        results: List["HOFVotingResult"]
    ) -> None:
        """Save all voting results for a year."""
        ...

    def get_candidate_voting_history(
        self,
        player_id: str
    ) -> List[Dict]:
        """Get complete voting history for a candidate."""
        ...

    def get_annual_voting_summary(
        self,
        voting_year: int
    ) -> Dict:
        """Get summary of voting for a specific year."""
        ...

    # ============ Eligibility Tracking ============

    def get_players_on_ballot(self) -> List[Dict]:
        """Get all players currently on HOF ballot."""
        ...

    def get_years_on_ballot(self, player_id: str) -> int:
        """Get how many years a player has been on ballot."""
        ...

    def is_inducted(self, player_id: str) -> bool:
        """Check if player is already in HOF."""
        ...

    # ============ Statistics ============

    def get_hof_stats(self) -> Dict:
        """Get overall HOF statistics for dynasty."""
        return {
            "total_members": self.get_inductee_count(),
            "first_ballot_count": self._count_first_ballot(),
            "by_position": self._count_by_position(),
            "by_team": self._count_by_team(),
            "average_wait_years": self._avg_years_to_induction(),
        }
```

### Acceptance Criteria
- [ ] All CRUD operations implemented
- [ ] Dynasty isolation enforced
- [ ] Voting history queryable
- [ ] Statistics calculations correct
- [ ] Unit tests for API methods

---

## Tollgate 7: OFFSEASON_HONORS Integration

**Goal**: Add HOF voting to the honors stage flow.

### Changes to `src/game_cycle/handlers/offseason.py`

```python
def handle_honors_stage(self, context: dict) -> dict:
    """
    Handle OFFSEASON_HONORS stage.

    Now includes:
    1. Super Bowl results display
    2. Award ceremony (MVP, All-Pro, etc.)
    3. Player retirements
    4. Hall of Fame voting <- NEW
    """
    # Existing code...

    # NEW: Hall of Fame voting
    hof_results = self._conduct_hof_voting(context)

    return {
        "super_bowl": super_bowl_results,
        "awards": award_results,
        "retirements": retirement_results,
        "hall_of_fame": hof_results,  # NEW
    }

def _conduct_hof_voting(self, context: dict) -> dict:
    """Conduct annual Hall of Fame voting."""
    dynasty_id = context["dynasty_id"]
    current_season = context["season"]

    # Get eligible candidates
    eligibility_service = HOFEligibilityService(...)
    candidates = eligibility_service.get_eligible_candidates(
        dynasty_id, current_season
    )

    if not candidates:
        return {"inductees": [], "message": "No eligible candidates this year."}

    # Score all candidates
    scoring_engine = HOFScoringEngine()
    for candidate in candidates:
        candidate.hof_score = scoring_engine.calculate_score(candidate).total_score

    # Conduct voting
    voting_engine = HOFVotingEngine()
    voting_session = voting_engine.conduct_voting(
        dynasty_id, current_season, candidates
    )

    # Save voting results
    hof_api = HOFAPI(self.gc_db.conn, dynasty_id)
    hof_api.save_voting_results(current_season, voting_session.all_results)

    # Create induction records and ceremonies
    induction_service = HOFInductionService(...)
    ceremonies = []
    for inductee in voting_session.inductees:
        ceremony = induction_service.create_induction(
            dynasty_id, inductee, self._get_candidate(inductee.player_id)
        )
        ceremonies.append(ceremony)

    # Generate headlines
    self._generate_hof_headlines(context, voting_session, ceremonies)

    return {
        "inductees": [c.__dict__ for c in ceremonies],
        "voting_results": voting_session.__dict__,
        "total_candidates": len(candidates),
    }
```

### HOF Headlines Generator

**File**: `src/game_cycle/services/headline_generators/hof_generator.py`

```python
class HOFGenerator(BaseHeadlineGenerator):
    """Generates headlines for Hall of Fame events."""

    @property
    def max_headlines(self) -> int:
        return 5  # One per inductee max

    def _generate_headline(
        self,
        event: TransactionEvent
    ) -> Optional[GeneratedHeadline]:
        """Generate headline for HOF induction."""
        inductee = event.details

        if inductee.get("is_first_ballot"):
            return self._generate_first_ballot_headline(event)
        else:
            return self._generate_standard_induction_headline(event)

    def _generate_first_ballot_headline(
        self,
        event: TransactionEvent
    ) -> GeneratedHeadline:
        """First-ballot inductees get special headlines."""
        return GeneratedHeadline(
            headline_type="HALL_OF_FAME",
            headline=f"{event.player_name} Inducted to Hall of Fame on First Ballot",
            subheadline=f"Canton welcomes legendary {event.player_position}",
            body_text=f"{event.player_name} has been inducted into the Pro Football Hall of Fame in their first year of eligibility, joining the sport's immortals in Canton. The {event.player_position} was selected by 97% of voters.",
            sentiment="HYPE",
            priority=90,
            team_ids=event.details.get("team_ids", []),
            player_ids=[event.player_id],
            metadata={"event_type": "hof_induction", "first_ballot": True}
        )
```

### Acceptance Criteria
- [ ] HOF voting runs during OFFSEASON_HONORS
- [ ] Results saved to database
- [ ] Headlines generated for inductees
- [ ] Induction ceremonies created
- [ ] Integration with existing honors flow seamless

---

## Tollgate 8: UI Implementation

**Goal**: Create UI components for Hall of Fame display.

### Component 1: HOF Tab in Awards View

**File**: `game_cycle_ui/views/awards_view.py` (modification)

Add new "Hall of Fame" tab alongside MVP, All-Pro, Pro Bowl tabs.

```python
def _create_hof_tab(self) -> QWidget:
    """Create Hall of Fame display tab."""
    widget = QWidget()
    layout = QVBoxLayout(widget)

    # Header
    header = QLabel("Pro Football Hall of Fame")
    header.setStyleSheet("font-size: 18px; font-weight: bold;")
    layout.addWidget(header)

    # Stats row (total inductees, first-ballot %, etc.)
    stats_row = self._create_hof_stats_row()
    layout.addWidget(stats_row)

    # Tabs: All Members | By Year | By Position | By Team
    self.hof_tabs = QTabWidget()
    self.hof_tabs.addTab(self._create_all_members_tab(), "All Members")
    self.hof_tabs.addTab(self._create_by_year_tab(), "By Year")
    self.hof_tabs.addTab(self._create_by_position_tab(), "By Position")
    self.hof_tabs.addTab(self._create_by_team_tab(), "By Team")
    layout.addWidget(self.hof_tabs)

    return widget
```

### Component 2: HOF Member Table

```python
def _create_all_members_tab(self) -> QWidget:
    """Table of all HOF members."""
    widget = QWidget()
    layout = QVBoxLayout(widget)

    # Search/filter
    filter_row = QHBoxLayout()
    self.hof_search = QLineEdit()
    self.hof_search.setPlaceholderText("Search by name...")
    filter_row.addWidget(self.hof_search)

    self.position_filter = QComboBox()
    self.position_filter.addItems(["All Positions", "QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB", "K/P"])
    filter_row.addWidget(self.position_filter)
    layout.addLayout(filter_row)

    # Table
    self.hof_table = QTableWidget()
    self.hof_table.setColumnCount(8)
    self.hof_table.setHorizontalHeaderLabels([
        "Name", "Position", "Year Inducted", "Years on Ballot",
        "Teams", "Championships", "MVPs", "All-Pro"
    ])
    layout.addWidget(self.hof_table)

    return widget
```

### Component 3: Induction Ceremony Dialog

**File**: `game_cycle_ui/dialogs/hof_induction_dialog.py`

```python
class HOFInductionDialog(QDialog):
    """
    Dialog displaying Hall of Fame induction ceremony.

    Shows:
    - Player bust image/description
    - Presenter introduction
    - Speech highlights
    - Career achievements
    - Gold jacket moment
    """

    def __init__(
        self,
        parent,
        inductees: List[Dict],
        theme
    ):
        super().__init__(parent)
        self.inductees = inductees
        self.theme = theme
        self.current_index = 0

        self.setWindowTitle("Hall of Fame Induction Ceremony")
        self.setMinimumSize(700, 600)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("PRO FOOTBALL HALL OF FAME")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #D4AF37;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # Inductee display area
        self.inductee_card = self._create_inductee_card()
        layout.addWidget(self.inductee_card)

        # Navigation buttons (if multiple inductees)
        if len(self.inductees) > 1:
            nav_row = QHBoxLayout()
            self.prev_btn = QPushButton("< Previous")
            self.prev_btn.clicked.connect(self._prev_inductee)
            nav_row.addWidget(self.prev_btn)

            self.page_label = QLabel(f"1 of {len(self.inductees)}")
            self.page_label.setAlignment(Qt.AlignCenter)
            nav_row.addWidget(self.page_label)

            self.next_btn = QPushButton("Next >")
            self.next_btn.clicked.connect(self._next_inductee)
            nav_row.addWidget(self.next_btn)
            layout.addLayout(nav_row)

        # Close button
        close_btn = QPushButton("Close Ceremony")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignCenter)

    def _create_inductee_card(self) -> QWidget:
        """Create card showing inductee details."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a2e, stop:1 #16213e);
                border: 2px solid #D4AF37;
                border-radius: 12px;
                padding: 20px;
            }
        """)

        layout = QVBoxLayout(card)

        # Name and position
        self.name_label = QLabel()
        self.name_label.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        self.name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.name_label)

        self.position_label = QLabel()
        self.position_label.setStyleSheet("font-size: 14px; color: #D4AF37;")
        self.position_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.position_label)

        # Bust description
        self.bust_label = QLabel()
        self.bust_label.setWordWrap(True)
        self.bust_label.setStyleSheet("font-style: italic; color: #888; margin: 10px 0;")
        layout.addWidget(self.bust_label)

        # Presenter introduction
        self.presenter_label = QLabel()
        self.presenter_label.setWordWrap(True)
        self.presenter_label.setStyleSheet("color: #ccc; margin: 5px 0;")
        layout.addWidget(self.presenter_label)

        # Speech highlights (scrollable)
        self.speech_area = QTextEdit()
        self.speech_area.setReadOnly(True)
        self.speech_area.setMinimumHeight(150)
        self.speech_area.setStyleSheet("""
            QTextEdit {
                background: rgba(0,0,0,0.3);
                color: white;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.speech_area)

        # Career achievements
        self.achievements_label = QLabel()
        self.achievements_label.setWordWrap(True)
        self.achievements_label.setStyleSheet("color: #D4AF37; margin-top: 10px;")
        layout.addWidget(self.achievements_label)

        return card

    def _display_inductee(self, index: int):
        """Display specific inductee."""
        inductee = self.inductees[index]

        self.name_label.setText(inductee["player_name"])
        self.position_label.setText(inductee["primary_position"])
        self.bust_label.setText(inductee.get("bust_description", ""))

        presenter = inductee.get("presenter_name", "")
        relationship = inductee.get("presenter_relationship", "")
        self.presenter_label.setText(f"Presented by: {presenter} ({relationship})")

        speech = inductee.get("speech_highlights", {})
        speech_text = "\n\n".join([
            f'"{speech.get("opening", "")}"',
            f'"{speech.get("career_reflection", "")}"',
            f'"{speech.get("thank_yous", "")}"',
            f'"{speech.get("legacy_statement", "")}"',
        ])
        self.speech_area.setText(speech_text)

        achievements = inductee.get("achievements", [])
        self.achievements_label.setText(" | ".join(achievements[:5]))
```

### Component 4: Team History HOF Section

Add HOF members to existing Team History / Team View:

```python
def _create_team_hof_section(self, team_id: int) -> QWidget:
    """Section showing team's Hall of Famers."""
    widget = QGroupBox("Hall of Fame Members")
    layout = QVBoxLayout(widget)

    # Get team's HOF members
    hof_api = HOFAPI(self.gc_db.conn, self.dynasty_id)
    team_name = self._get_team_name(team_id)
    hof_members = hof_api.get_team_hof_members(team_name)

    if not hof_members:
        empty_label = QLabel("No Hall of Fame members yet")
        empty_label.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(empty_label)
    else:
        for member in hof_members:
            member_row = QHBoxLayout()

            name = QLabel(member["player_name"])
            name.setStyleSheet("font-weight: bold;")
            member_row.addWidget(name)

            position = QLabel(member["primary_position"])
            position.setStyleSheet("color: #888;")
            member_row.addWidget(position)

            year = QLabel(f"Class of {member['induction_year']}")
            year.setStyleSheet("color: #D4AF37;")
            member_row.addWidget(year)

            member_row.addStretch()
            layout.addLayout(member_row)

    return widget
```

### Acceptance Criteria
- [ ] HOF tab in Awards View displays all inductees
- [ ] Filtering by position, team, year works
- [ ] Induction Ceremony Dialog shows speech highlights
- [ ] Team History includes HOF section
- [ ] UI styling matches ESPN/Canton aesthetic

---

## Testing Strategy

### Unit Tests

```python
# tests/game_cycle/services/test_hof_eligibility_service.py

def test_five_year_waiting_period():
    """Players must wait 5 years after retirement."""
    service = HOFEligibilityService(...)
    # Retired in 2024, current season 2027 (3 years) = not eligible
    status = service.check_eligibility(player_id, 2024, 2027, stats, "QB")
    assert status == EligibilityStatus.TOO_RECENT

def test_career_minimums_enforced():
    """Players must meet position minimums."""
    service = HOFEligibilityService(...)
    # QB with only 10000 yards (needs 15000)
    stats = {"passing_yards": 10000, "passing_tds": 80}
    status = service.check_eligibility(player_id, 2020, 2026, stats, "QB")
    assert status == EligibilityStatus.BELOW_MINIMUM

def test_twenty_year_ballot_limit():
    """Players removed after 20 years on ballot."""
    service = HOFEligibilityService(...)
    # Eligible since 2005, now 2026 (21 years)
    status = service.check_eligibility(player_id, 2000, 2026, stats, "WR")
    assert status == EligibilityStatus.REMOVED_FROM_BALLOT
```

```python
# tests/game_cycle/services/test_hof_scoring_engine.py

def test_first_ballot_threshold():
    """85+ score = first ballot tier."""
    engine = HOFScoringEngine()
    candidate = create_elite_candidate(mvp=2, all_pro=8, rings=2)
    breakdown = engine.calculate_score(candidate)
    assert breakdown.total_score >= 85
    assert breakdown.tier == HOFTier.FIRST_BALLOT

def test_borderline_candidate():
    """55-69 score = borderline tier."""
    engine = HOFScoringEngine()
    candidate = create_good_candidate(mvp=0, all_pro=3, rings=0)
    breakdown = engine.calculate_score(candidate)
    assert 55 <= breakdown.total_score < 70
    assert breakdown.tier == HOFTier.BORDERLINE

def test_position_specific_scoring():
    """Stats scored relative to position thresholds."""
    engine = HOFScoringEngine()
    # QB with 60000 yards (above 50000 threshold) should score high
    qb = create_candidate("QB", passing_yards=60000, passing_tds=400)
    breakdown = engine.calculate_score(qb)
    assert breakdown.stats_score >= 20  # Near max for stats factor
```

```python
# tests/game_cycle/services/test_hof_voting_engine.py

def test_max_five_inductees():
    """Even with 10 qualifying candidates, max 5 inducted."""
    engine = HOFVotingEngine()
    candidates = [create_first_ballot_candidate() for _ in range(10)]
    session = engine.conduct_voting("dynasty1", 2026, candidates)
    assert len(session.inductees) <= 5

def test_induction_threshold():
    """Must get 80% to be inducted."""
    engine = HOFVotingEngine()
    candidate = create_borderline_candidate()  # ~60% expected
    session = engine.conduct_voting("dynasty1", 2026, [candidate])
    assert len(session.inductees) == 0

def test_ballot_removal_at_five_percent():
    """Candidates below 5% removed from ballot."""
    engine = HOFVotingEngine()
    candidate = create_weak_candidate()  # <5% expected
    session = engine.conduct_voting("dynasty1", 2026, [candidate])
    assert len(session.removed_from_ballot) == 1
```

### Integration Tests

```python
# tests/game_cycle/integration/test_hof_flow.py

def test_full_hof_voting_flow():
    """Test complete HOF voting during honors stage."""
    # Setup: Create dynasty with retired players
    # Action: Run OFFSEASON_HONORS
    # Verify: HOF voting completed, inductees saved, headlines generated
    ...

def test_hof_induction_ceremony_created():
    """Test ceremony data generated for inductees."""
    # Setup: Induct first-ballot candidate
    # Verify: Ceremony has speech, presenter, achievements
    ...
```

---

## Migration Notes

### Adding HOF to Existing Dynasties

For dynasties with existing retired players:
1. Backfill eligibility based on retirement year
2. Skip voting for past years (no retroactive voting)
3. Begin voting in current season

```python
def migrate_hof_for_existing_dynasty(dynasty_id: str, current_season: int):
    """Prepare existing dynasty for HOF feature."""
    # Get all retired players
    retired = get_retired_players(dynasty_id)

    # For each, calculate years since retirement
    for player in retired:
        years_since = current_season - player.retirement_year
        if years_since >= 5:
            # Mark as eligible for current season voting
            mark_hof_eligible(player.player_id, current_season)
```

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| First-ballot rate | 20-30% | Track % of inductees who are first-ballot |
| Average wait years | 3-7 years | Track average years on ballot before induction |
| Inductions per year | 2-5 | Should rarely hit 5 max limit |
| Player satisfaction | High | No complaints about unrealistic voting |
| UI usability | High | Users can easily browse HOF history |

---

## Appendix: Sample Scoring Scenarios

### First-Ballot Lock (Score: 92)

**Tom Brady-type QB**
- 3x MVP (75 pts from awards)
- 7x Super Bowl Champion (84 pts from championships)
- 15x Pro Bowl, 3x All-Pro First Team
- 89,000 passing yards, 649 TDs
- 23 seasons

Score Breakdown:
- Awards: 28/30 (MVP dominance)
- Championships: 15/15 (max)
- Stats: 24/25 (elite across board)
- Longevity: 15/15 (23 seasons)
- Peak: 13/15 (3 elite seasons)
- **Total: 95** → First Ballot

### Strong Candidate (Score: 76)

**Pro Bowl WR, 1 Ring**
- 0 MVP, 5x Pro Bowl, 2x All-Pro Second Team
- 1 Super Bowl
- 12,500 receiving yards, 800 receptions, 75 TDs
- 12 seasons

Score Breakdown:
- Awards: 14/30
- Championships: 12/15
- Stats: 20/25
- Longevity: 12/15
- Peak: 11/15
- **Total: 69** → Strong (borderline first-ballot)

### Borderline (Score: 58)

**Good LB, No Rings**
- 0 MVP, 4x Pro Bowl, 0 All-Pro
- 0 Super Bowls
- 1,100 tackles, 35 sacks
- 11 seasons

Score Breakdown:
- Awards: 8/30
- Championships: 0/15
- Stats: 18/25
- Longevity: 10/15
- Peak: 8/15
- **Total: 44** → Long Shot

---

## Appendix: UI Mockups

### HOF Tab Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  PRO FOOTBALL HALL OF FAME                                          │
│  ─────────────────────────────────────────────────────────────────  │
│  Total Members: 47 │ First-Ballot: 23 (49%) │ Avg Wait: 4.2 years   │
├─────────────────────────────────────────────────────────────────────┤
│  [All Members] [By Year] [By Position] [By Team]                    │
├─────────────────────────────────────────────────────────────────────┤
│  Search: [___________]  Position: [All ▼]  Team: [All ▼]            │
├─────────────────────────────────────────────────────────────────────┤
│  Name             │ Pos │ Year │ Wait │ Teams      │ SB │ MVP │ AP  │
│  ─────────────────────────────────────────────────────────────────  │
│  Tom Brady        │ QB  │ 2030 │  1   │ NE, TB     │ 7  │ 3   │ 3   │
│  Patrick Mahomes  │ QB  │ 2042 │  1   │ KC         │ 4  │ 3   │ 4   │
│  Aaron Donald     │ DT  │ 2033 │  1   │ LA         │ 1  │ 0   │ 8   │
│  Tyreek Hill      │ WR  │ 2039 │  3   │ KC, MIA    │ 1  │ 0   │ 3   │
│  ...                                                                │
└─────────────────────────────────────────────────────────────────────┘
```

### Induction Ceremony Dialog

```
┌─────────────────────────────────────────────────────────────────────┐
│                   PRO FOOTBALL HALL OF FAME                         │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                                                             │   │
│  │                     PATRICK MAHOMES                         │   │
│  │                      Quarterback                            │   │
│  │                                                             │   │
│  │  "The bronze bust captures the intensity in his eyes,       │   │
│  │   the same look that preceded countless comebacks..."       │   │
│  │                                                             │   │
│  │  Presented by: Travis Kelce (Former Teammate)               │   │
│  │                                                             │   │
│  │  ┌───────────────────────────────────────────────────────┐ │   │
│  │  │ "Standing here in Canton, I'm overwhelmed. When       │ │   │
│  │  │  Coach Reid took a chance on me, I never imagined...  │ │   │
│  │  │                                                        │ │   │
│  │  │  To my teammates who went to war with me every Sunday  │ │   │
│  │  │  - this is ours. To Chiefs Kingdom - I love you."     │ │   │
│  │  └───────────────────────────────────────────────────────┘ │   │
│  │                                                             │   │
│  │  4x Super Bowl Champion │ 3x MVP │ 4x All-Pro              │   │
│  │                                                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│                      < Previous  [1 of 3]  Next >                   │
│                                                                     │
│                        [Close Ceremony]                             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```
