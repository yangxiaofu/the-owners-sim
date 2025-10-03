"""
Playoff Seeding Data Models

Data structures for representing NFL playoff seeding calculations.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class PlayoffSeed:
    """
    Represents a single playoff seed.

    Contains complete team information and seeding context.
    """
    seed: int                      # 1-7
    team_id: int                   # NFL team ID (1-32)
    wins: int
    losses: int
    ties: int
    win_percentage: float
    division_winner: bool          # True for seeds 1-4
    division_name: str             # e.g., "AFC North"
    conference: str                # "AFC" or "NFC"
    points_for: int
    points_against: int
    point_differential: int
    division_record: str           # e.g., "5-1"
    conference_record: str         # e.g., "9-3"
    tiebreaker_notes: Optional[str] = None  # Description of tiebreaker applied

    @property
    def record_string(self) -> str:
        """Get record as string (e.g., '13-4' or '10-6-1')."""
        if self.ties > 0:
            return f"{self.wins}-{self.losses}-{self.ties}"
        return f"{self.wins}-{self.losses}"

    @property
    def seed_label(self) -> str:
        """Get seed label (e.g., '#1 Seed' or 'Wild Card')."""
        if self.seed == 1:
            return "#1 Seed (Bye)"
        elif self.seed <= 4:
            return f"#{self.seed} Seed (Division Winner)"
        else:
            return f"#{self.seed} Seed (Wild Card)"


@dataclass
class ConferenceSeeding:
    """
    Seeding for a single conference (AFC or NFC).

    Contains all 7 playoff seeds plus playoff status information.
    """
    conference: str                    # "AFC" or "NFC"
    seeds: List[PlayoffSeed]           # 7 seeds, ordered 1-7
    division_winners: List[PlayoffSeed]  # First 4 seeds
    wildcards: List[PlayoffSeed]       # Last 3 seeds
    clinched_teams: List[int]          # Team IDs that clinched playoff berth
    eliminated_teams: List[int]        # Team IDs mathematically eliminated

    def get_seed_by_number(self, seed_number: int) -> Optional[PlayoffSeed]:
        """Get seed by seed number (1-7)."""
        for seed in self.seeds:
            if seed.seed == seed_number:
                return seed
        return None

    def get_seed_by_team(self, team_id: int) -> Optional[PlayoffSeed]:
        """Get seed for a specific team."""
        for seed in self.seeds:
            if seed.team_id == team_id:
                return seed
        return None

    def is_clinched(self, team_id: int) -> bool:
        """Check if team has clinched playoff berth."""
        return team_id in self.clinched_teams

    def is_eliminated(self, team_id: int) -> bool:
        """Check if team is eliminated from playoffs."""
        return team_id in self.eliminated_teams


@dataclass
class PlayoffSeeding:
    """
    Complete playoff seeding for both conferences.

    This is the main output of the PlayoffSeeder calculation.
    Can be calculated at any point during the season (weeks 10-18).
    """
    season: int                        # Season year (e.g., 2024)
    week: int                          # Week when calculated (10-18)
    afc: ConferenceSeeding            # AFC seeding
    nfc: ConferenceSeeding            # NFC seeding
    tiebreakers_applied: List[Dict[str, Any]]  # Record of tiebreaker usage
    calculation_date: str              # ISO format timestamp

    def get_seed(self, team_id: int) -> Optional[PlayoffSeed]:
        """
        Get playoff seed for a specific team (searches both conferences).

        Args:
            team_id: Team ID to look up

        Returns:
            PlayoffSeed if team is in playoff position, None otherwise
        """
        # Check AFC first (teams 1-16)
        if 1 <= team_id <= 16:
            return self.afc.get_seed_by_team(team_id)
        # Check NFC (teams 17-32)
        else:
            return self.nfc.get_seed_by_team(team_id)

    def is_in_playoffs(self, team_id: int) -> bool:
        """
        Check if team is currently in playoff position.

        Args:
            team_id: Team ID to check

        Returns:
            True if team is seeded 1-7 in their conference
        """
        seed = self.get_seed(team_id)
        return seed is not None and seed.seed <= 7

    def is_clinched(self, team_id: int) -> bool:
        """Check if team has clinched playoff berth."""
        if 1 <= team_id <= 16:
            return self.afc.is_clinched(team_id)
        else:
            return self.nfc.is_clinched(team_id)

    def is_eliminated(self, team_id: int) -> bool:
        """Check if team is eliminated from playoffs."""
        if 1 <= team_id <= 16:
            return self.afc.is_eliminated(team_id)
        else:
            return self.nfc.is_eliminated(team_id)

    def get_matchups(self) -> Dict[str, List[tuple]]:
        """
        Get potential wild card round matchups.

        Returns:
            Dictionary with AFC and NFC matchups:
            {
                'AFC': [(2, 7), (3, 6), (4, 5)],
                'NFC': [(2, 7), (3, 6), (4, 5)]
            }
        """
        return {
            'AFC': [
                (self.afc.seeds[1].team_id, self.afc.seeds[6].team_id),  # 2 vs 7
                (self.afc.seeds[2].team_id, self.afc.seeds[5].team_id),  # 3 vs 6
                (self.afc.seeds[3].team_id, self.afc.seeds[4].team_id),  # 4 vs 5
            ],
            'NFC': [
                (self.nfc.seeds[1].team_id, self.nfc.seeds[6].team_id),  # 2 vs 7
                (self.nfc.seeds[2].team_id, self.nfc.seeds[5].team_id),  # 3 vs 6
                (self.nfc.seeds[3].team_id, self.nfc.seeds[4].team_id),  # 4 vs 5
            ]
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'season': self.season,
            'week': self.week,
            'calculation_date': self.calculation_date,
            'afc': {
                'seeds': [
                    {
                        'seed': s.seed,
                        'team_id': s.team_id,
                        'wins': s.wins,
                        'losses': s.losses,
                        'ties': s.ties,
                        'division_name': s.division_name,
                        'record': s.record_string,
                        'win_percentage': s.win_percentage,
                        'division_winner': s.division_winner,
                        'points_for': s.points_for,
                        'points_against': s.points_against
                    }
                    for s in self.afc.seeds
                ]
            },
            'nfc': {
                'seeds': [
                    {
                        'seed': s.seed,
                        'team_id': s.team_id,
                        'wins': s.wins,
                        'losses': s.losses,
                        'ties': s.ties,
                        'division_name': s.division_name,
                        'record': s.record_string,
                        'win_percentage': s.win_percentage,
                        'division_winner': s.division_winner,
                        'points_for': s.points_for,
                        'points_against': s.points_against
                    }
                    for s in self.nfc.seeds
                ]
            },
            'tiebreakers_applied': self.tiebreakers_applied
        }
