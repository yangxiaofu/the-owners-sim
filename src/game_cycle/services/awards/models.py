"""
Award System Models.

Dataclasses and enums for award eligibility and scoring.
Part of Milestone 10: Awards System, Tollgate 2.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AwardType(Enum):
    """Types of awards that can be scored."""
    MVP = "mvp"
    OPOY = "opoy"
    DPOY = "dpoy"
    OROY = "oroy"
    DROY = "droy"
    CPOY = "cpoy"


# Position group mappings
OFFENSIVE_POSITIONS = frozenset([
    'QB', 'RB', 'FB', 'WR', 'TE',
    'LT', 'LG', 'C', 'RG', 'RT',
    'OL',  # Generic offensive line
])

DEFENSIVE_POSITIONS = frozenset([
    'LE', 'DT', 'RE', 'NT', 'DE',  # Added 'DE' (standard defensive end abbreviation)
    'LOLB', 'MLB', 'ROLB', 'ILB', 'OLB',
    'MIKE', 'WILL', 'SAM',  # Added LB variants
    'CB', 'FS', 'SS', 'S',
    'EDGE',  # Edge rusher
    'DL', 'LB', 'DB',  # Generic positions
])

SPECIAL_TEAMS_POSITIONS = frozenset(['K', 'P', 'LS', 'KR', 'PR'])


@dataclass
class PlayerCandidate:
    """
    A candidate for an award with all relevant data populated.

    Combines stats, grades, and team success metrics needed for scoring.
    """
    player_id: int
    player_name: str
    team_id: int
    position: str
    season: int

    # Stats fields (from StatsAPI)
    games_played: int = 0
    passing_yards: int = 0
    passing_tds: int = 0
    passing_interceptions: int = 0
    passer_rating: float = 0.0
    rushing_yards: int = 0
    rushing_tds: int = 0
    receiving_yards: int = 0
    receiving_tds: int = 0
    receptions: int = 0
    sacks: float = 0.0
    interceptions: int = 0
    tackles_total: int = 0
    forced_fumbles: int = 0

    # Grade fields (from AnalyticsAPI)
    overall_grade: float = 0.0
    position_grade: float = 0.0
    position_rank: Optional[int] = None
    overall_rank: Optional[int] = None
    epa_total: float = 0.0
    total_snaps: int = 0

    # Defensive grade fields (for position-specific scoring)
    pass_rush_grade: float = 0.0
    coverage_grade: float = 0.0
    tackling_grade: float = 0.0
    run_defense_grade: float = 0.0

    # OL blocking grade fields (for position-specific scoring)
    pass_blocking_grade: float = 0.0
    run_blocking_grade: float = 0.0

    # Team success fields (from StandingsAPI/PlayoffBracketAPI)
    team_wins: int = 0
    team_losses: int = 0
    win_percentage: float = 0.0
    playoff_seed: Optional[int] = None
    is_division_winner: bool = False
    is_conference_champion: bool = False

    # Rookie/CPOY fields
    years_pro: int = 0
    previous_season_grade: Optional[float] = None
    games_missed_previous: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'player_id': self.player_id,
            'player_name': self.player_name,
            'team_id': self.team_id,
            'position': self.position,
            'season': self.season,
            'games_played': self.games_played,
            'passing_yards': self.passing_yards,
            'passing_tds': self.passing_tds,
            'passing_interceptions': self.passing_interceptions,
            'passer_rating': self.passer_rating,
            'rushing_yards': self.rushing_yards,
            'rushing_tds': self.rushing_tds,
            'receiving_yards': self.receiving_yards,
            'receiving_tds': self.receiving_tds,
            'receptions': self.receptions,
            'sacks': self.sacks,
            'interceptions': self.interceptions,
            'tackles_total': self.tackles_total,
            'forced_fumbles': self.forced_fumbles,
            'overall_grade': self.overall_grade,
            'position_grade': self.position_grade,
            'position_rank': self.position_rank,
            'overall_rank': self.overall_rank,
            'epa_total': self.epa_total,
            'total_snaps': self.total_snaps,
            'pass_rush_grade': self.pass_rush_grade,
            'coverage_grade': self.coverage_grade,
            'tackling_grade': self.tackling_grade,
            'run_defense_grade': self.run_defense_grade,
            'pass_blocking_grade': self.pass_blocking_grade,
            'run_blocking_grade': self.run_blocking_grade,
            'team_wins': self.team_wins,
            'team_losses': self.team_losses,
            'win_percentage': self.win_percentage,
            'playoff_seed': self.playoff_seed,
            'is_division_winner': self.is_division_winner,
            'is_conference_champion': self.is_conference_champion,
            'years_pro': self.years_pro,
            'previous_season_grade': self.previous_season_grade,
            'games_missed_previous': self.games_missed_previous,
        }

    @property
    def is_rookie(self) -> bool:
        """Check if player is a rookie (years_pro == 0)."""
        return self.years_pro == 0

    @property
    def position_group(self) -> str:
        """Get the position group ('offense', 'defense', 'special_teams')."""
        if self.position in OFFENSIVE_POSITIONS:
            return 'offense'
        elif self.position in DEFENSIVE_POSITIONS:
            return 'defense'
        elif self.position in SPECIAL_TEAMS_POSITIONS:
            return 'special_teams'
        else:
            # Default to offense for unknown positions
            return 'offense'

    @property
    def total_yards(self) -> int:
        """Total yards from scrimmage (rushing + receiving)."""
        return self.rushing_yards + self.receiving_yards

    @property
    def total_tds(self) -> int:
        """Total touchdowns (rushing + receiving)."""
        return self.rushing_tds + self.receiving_tds


@dataclass
class AwardScore:
    """
    Scoring breakdown for a candidate for a specific award.

    Contains component scores that combine into the final score.
    """
    player_id: int
    player_name: str
    team_id: int
    position: str
    award_type: AwardType

    # Component scores (0-100 scale)
    stat_component: float = 0.0
    grade_component: float = 0.0
    team_success_component: float = 0.0

    # Weighted total before position multiplier
    total_score: float = 0.0

    # Position multiplier (MVP only, 1.0 default)
    position_multiplier: float = 1.0

    # Detailed breakdown for UI/debugging
    breakdown: Dict[str, Any] = field(default_factory=dict)

    @property
    def final_score(self) -> float:
        """Final score after applying position multiplier."""
        return self.total_score * self.position_multiplier

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'player_id': self.player_id,
            'player_name': self.player_name,
            'team_id': self.team_id,
            'position': self.position,
            'award_type': self.award_type.value,
            'stat_component': self.stat_component,
            'grade_component': self.grade_component,
            'team_success_component': self.team_success_component,
            'total_score': self.total_score,
            'position_multiplier': self.position_multiplier,
            'final_score': self.final_score,
            'breakdown': self.breakdown,
        }


@dataclass
class EligibilityResult:
    """
    Result of checking a player's eligibility for an award.

    Contains eligibility status and reasons for ineligibility.
    """
    player_id: int
    player_name: str
    is_eligible: bool
    reasons: List[str] = field(default_factory=list)
    games_played: int = 0
    total_snaps: int = 0
    is_rookie: bool = False
    position_group: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'player_id': self.player_id,
            'player_name': self.player_name,
            'is_eligible': self.is_eligible,
            'reasons': self.reasons,
            'games_played': self.games_played,
            'total_snaps': self.total_snaps,
            'is_rookie': self.is_rookie,
            'position_group': self.position_group,
        }
