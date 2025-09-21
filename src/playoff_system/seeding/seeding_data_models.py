"""
Playoff Seeding Data Models

Core data structures for NFL playoff seeding calculations and results.
These models represent the output of playoff seeding calculations and
provide the interface for the playoff management system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from enum import Enum


class TiebreakerRule(Enum):
    """NFL tiebreaker rules in order of application"""
    HEAD_TO_HEAD = "head_to_head"
    DIVISION_RECORD = "division_record"
    CONFERENCE_RECORD = "conference_record"
    COMMON_GAMES = "common_games"
    STRENGTH_OF_VICTORY = "strength_of_victory"
    STRENGTH_OF_SCHEDULE = "strength_of_schedule"
    COMBINED_RANKING_CONFERENCE = "combined_ranking_conference"
    COMBINED_RANKING_ALL = "combined_ranking_all"
    NET_POINTS_CONFERENCE = "net_points_conference"
    NET_POINTS_ALL = "net_points_all"
    COIN_FLIP = "coin_flip"


class PlayoffRound(Enum):
    """NFL playoff rounds"""
    WILD_CARD = "wild_card"
    DIVISIONAL = "divisional"
    CONFERENCE = "conference"
    SUPER_BOWL = "super_bowl"


@dataclass
class TeamRecord:
    """
    Complete team record for tiebreaker calculations.

    Contains all the data needed to apply NFL tiebreaker rules.
    """
    team_id: int
    wins: int
    losses: int
    ties: int = 0

    # Division and conference records
    division_wins: int = 0
    division_losses: int = 0
    division_ties: int = 0
    conference_wins: int = 0
    conference_losses: int = 0
    conference_ties: int = 0

    # Home/away splits
    home_wins: int = 0
    home_losses: int = 0
    home_ties: int = 0
    away_wins: int = 0
    away_losses: int = 0
    away_ties: int = 0

    # Scoring
    points_for: int = 0
    points_against: int = 0

    # Strength calculations (calculated by engine)
    strength_of_victory: float = 0.0
    strength_of_schedule: float = 0.0

    # Head-to-head records (populated during tiebreaker calculation)
    head_to_head_records: Dict[int, str] = field(default_factory=dict)  # opponent_id -> "2-0", "1-1", etc.

    # Common games record (calculated during tiebreaker)
    common_games_record: Optional[str] = None

    @property
    def overall_record(self) -> str:
        """Get overall record as string"""
        if self.ties > 0:
            return f"{self.wins}-{self.losses}-{self.ties}"
        return f"{self.wins}-{self.losses}"

    @property
    def win_percentage(self) -> float:
        """Calculate win percentage (ties count as 0.5 wins)"""
        total_games = self.wins + self.losses + self.ties
        if total_games == 0:
            return 0.0
        return (self.wins + 0.5 * self.ties) / total_games

    @property
    def point_differential(self) -> int:
        """Calculate point differential"""
        return self.points_for - self.points_against

    @property
    def division_win_percentage(self) -> float:
        """Calculate division win percentage"""
        total_division_games = self.division_wins + self.division_losses + self.division_ties
        if total_division_games == 0:
            return 0.0
        return (self.division_wins + 0.5 * self.division_ties) / total_division_games

    @property
    def conference_win_percentage(self) -> float:
        """Calculate conference win percentage"""
        total_conference_games = self.conference_wins + self.conference_losses + self.conference_ties
        if total_conference_games == 0:
            return 0.0
        return (self.conference_wins + 0.5 * self.conference_ties) / total_conference_games


@dataclass
class TiebreakerResult:
    """
    Result of applying a specific tiebreaker rule.

    Documents which rule was applied, which teams were involved,
    and the calculation details for transparency.
    """
    rule_applied: TiebreakerRule
    teams_involved: List[int]  # Team IDs that were tied
    winner_team_id: int  # Team that won the tiebreaker
    eliminated_teams: List[int]  # Teams eliminated by this tiebreaker
    calculation_details: Dict[str, Any]  # Detailed breakdown of calculation
    description: str  # Human-readable description of what happened

    @property
    def was_decisive(self) -> bool:
        """True if this tiebreaker resolved the entire tie"""
        return len(self.eliminated_teams) == len(self.teams_involved) - 1


@dataclass
class PlayoffSeed:
    """
    Individual team's playoff seed information.

    Represents one team's position in the playoff seeding,
    including all relevant context about how they qualified.
    """
    seed_number: int  # 1-7
    team_id: int
    record: str  # "14-3", "11-6", etc.
    win_percentage: float
    division_winner: bool
    conference: str  # "AFC" or "NFC"
    division: str  # "AFC East", "NFC North", etc.

    # Tiebreaker information
    tiebreaker_won: Optional[TiebreakerRule] = None
    tiebreaker_description: Optional[str] = None
    eliminated_teams: List[int] = field(default_factory=list)

    # Additional context
    points_for: int = 0
    points_against: int = 0
    strength_of_victory: float = 0.0
    strength_of_schedule: float = 0.0

    @property
    def seed_type(self) -> str:
        """Get seed type description"""
        if self.division_winner:
            return f"Division Winner (#{self.seed_number})"
        else:
            return f"Wild Card (#{self.seed_number})"

    @property
    def point_differential(self) -> int:
        """Calculate point differential"""
        return self.points_for - self.points_against


@dataclass
class WildCardMatchup:
    """
    Wild card round matchup information.

    Represents a single wild card playoff game with all context.
    """
    higher_seed: PlayoffSeed
    lower_seed: PlayoffSeed
    home_team_id: int  # Always the higher seed
    away_team_id: int  # Always the lower seed
    conference: str  # "AFC" or "NFC"
    game_description: str  # "AFC Wild Card: Bills (2) vs Dolphins (7)"

    @property
    def seed_matchup(self) -> str:
        """Get seed matchup string like '2 vs 7'"""
        return f"{self.higher_seed.seed_number} vs {self.lower_seed.seed_number}"


@dataclass
class PlayoffSeeding:
    """
    Complete playoff seeding results for both conferences.

    This is the main output of the playoff seeding calculation,
    containing all seeded teams and playoff matchups.
    """
    # Seeding results
    afc_seeds: List[PlayoffSeed]  # Seeds 1-7 in order
    nfc_seeds: List[PlayoffSeed]  # Seeds 1-7 in order

    # Wild card matchups (generated from seeding)
    wild_card_matchups: List[WildCardMatchup]  # 6 games total (3 per conference)

    # Metadata
    dynasty_id: str
    season: int
    seeding_date: datetime

    # Tiebreaker tracking
    tiebreaker_applications: List[TiebreakerResult] = field(default_factory=list)

    # Additional context
    regular_season_complete: bool = True
    calculation_time_seconds: float = 0.0

    @property
    def all_playoff_teams(self) -> List[PlayoffSeed]:
        """Get all 14 playoff teams combined"""
        return self.afc_seeds + self.nfc_seeds

    @property
    def division_winners(self) -> List[PlayoffSeed]:
        """Get all 8 division winners"""
        return [seed for seed in self.all_playoff_teams if seed.division_winner]

    @property
    def wild_card_teams(self) -> List[PlayoffSeed]:
        """Get all 6 wild card teams"""
        return [seed for seed in self.all_playoff_teams if not seed.division_winner]

    @property
    def teams_with_byes(self) -> List[PlayoffSeed]:
        """Get the 2 teams with first-round byes (1 seeds)"""
        return [seed for seed in self.all_playoff_teams if seed.seed_number == 1]

    def get_conference_seeds(self, conference: str) -> List[PlayoffSeed]:
        """Get seeds for specific conference"""
        if conference.upper() == "AFC":
            return self.afc_seeds
        elif conference.upper() == "NFC":
            return self.nfc_seeds
        else:
            raise ValueError(f"Invalid conference: {conference}")

    def get_seed_by_team(self, team_id: int) -> Optional[PlayoffSeed]:
        """Get playoff seed for specific team"""
        for seed in self.all_playoff_teams:
            if seed.team_id == team_id:
                return seed
        return None

    def get_matchups_by_conference(self, conference: str) -> List[WildCardMatchup]:
        """Get wild card matchups for specific conference"""
        return [matchup for matchup in self.wild_card_matchups
                if matchup.conference.upper() == conference.upper()]


@dataclass
class PlayoffSeedingInput:
    """
    Input data required for playoff seeding calculation.

    Consolidates all the data needed from various stores.
    """
    final_standings: Dict[int, TeamRecord]  # team_id -> TeamRecord
    head_to_head_results: Dict[tuple, str]  # (team1_id, team2_id) -> "1-1", "2-0", etc.
    dynasty_id: str
    season: int
    calculation_date: datetime = field(default_factory=datetime.now)

    @property
    def afc_teams(self) -> Dict[int, TeamRecord]:
        """Get AFC teams (team IDs 1-16)"""
        return {tid: record for tid, record in self.final_standings.items() if 1 <= tid <= 16}

    @property
    def nfc_teams(self) -> Dict[int, TeamRecord]:
        """Get NFC teams (team IDs 17-32)"""
        return {tid: record for tid, record in self.final_standings.items() if 17 <= tid <= 32}

    def get_division_teams(self, division: str) -> Dict[int, TeamRecord]:
        """Get teams from specific division"""
        # NFL division mappings
        divisions = {
            'AFC_EAST': [1, 2, 3, 4],
            'AFC_NORTH': [5, 6, 7, 8],
            'AFC_SOUTH': [9, 10, 11, 12],
            'AFC_WEST': [13, 14, 15, 16],
            'NFC_EAST': [17, 18, 19, 20],
            'NFC_NORTH': [21, 22, 23, 24],
            'NFC_SOUTH': [25, 26, 27, 28],
            'NFC_WEST': [29, 30, 31, 32]
        }

        team_ids = divisions.get(division.upper(), [])
        return {tid: self.final_standings[tid] for tid in team_ids if tid in self.final_standings}