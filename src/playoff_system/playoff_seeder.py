"""
Playoff Seeder

Calculates NFL playoff seeding from current standings.
Pure calculation logic - no database access or side effects.
Can calculate seeding at any point in the season (weeks 10-18).
"""

from typing import Dict, Any, List, Union
from datetime import datetime

from stores.standings_store import StandingsStore, EnhancedTeamStanding, NFL_DIVISIONS
from .seeding_models import PlayoffSeeding, ConferenceSeeding, PlayoffSeed


class PlayoffSeeder:
    """
    Calculates NFL playoff seeding based on current standings.

    Usage:
        # With live standings store
        seeder = PlayoffSeeder()
        seeding = seeder.calculate_seeding(standings_store, season=2024, week=12)

        # With snapshot data (dict of EnhancedTeamStanding)
        standings_data = {...}
        seeding = seeder.calculate_seeding(standings_data, season=2024, week=12)

    The seeder can be used:
    - During season (weeks 10-18) for real-time playoff picture
    - At end of season for final seeding
    - With mock data for testing
    - With live StandingsStore for actual simulations
    """

    def __init__(self):
        """Initialize playoff seeder."""
        self.tiebreakers_applied: List[Dict[str, Any]] = []

    def calculate_seeding(
        self,
        standings: Union[StandingsStore, Dict[int, EnhancedTeamStanding]],
        season: int,
        week: int
    ) -> PlayoffSeeding:
        """
        Calculate playoff seeding from standings.

        Args:
            standings: StandingsStore instance or dict of EnhancedTeamStanding
            season: Season year (e.g., 2024)
            week: Current week (10-18 for meaningful seeding)

        Returns:
            PlayoffSeeding with complete seeding for both conferences
        """
        # Reset tiebreakers for this calculation
        self.tiebreakers_applied = []

        # Convert to standardized format if needed
        if isinstance(standings, StandingsStore):
            standings_data = self._extract_standings_data(standings)
        else:
            standings_data = standings

        # Calculate seeding for each conference
        afc_seeding = self._calculate_conference_seeding(
            standings_data, 'AFC', season, week
        )
        nfc_seeding = self._calculate_conference_seeding(
            standings_data, 'NFC', season, week
        )

        return PlayoffSeeding(
            season=season,
            week=week,
            afc=afc_seeding,
            nfc=nfc_seeding,
            tiebreakers_applied=self.tiebreakers_applied,
            calculation_date=datetime.now().isoformat()
        )

    def _extract_standings_data(
        self,
        standings_store: StandingsStore
    ) -> Dict[int, EnhancedTeamStanding]:
        """
        Extract standings data from StandingsStore.

        Args:
            standings_store: StandingsStore instance

        Returns:
            Dictionary mapping team_id to EnhancedTeamStanding
        """
        standings_dict = {}
        for team_id in range(1, 33):
            standing = standings_store.get_team_standing(team_id)
            if standing:
                standings_dict[team_id] = standing
        return standings_dict

    def _calculate_conference_seeding(
        self,
        standings_data: Dict[int, EnhancedTeamStanding],
        conference: str,
        season: int,
        week: int
    ) -> ConferenceSeeding:
        """
        Calculate seeding for a single conference.

        Args:
            standings_data: Dict of team standings
            conference: 'AFC' or 'NFC'
            season: Season year
            week: Current week

        Returns:
            ConferenceSeeding with 7 playoff seeds
        """
        # Step 1: Identify division winners
        division_winners = self._get_division_winners(standings_data, conference)

        # Step 2: Sort division winners by record (seeds 1-4)
        division_winners = self._sort_teams_by_record(division_winners)

        # Step 3: Identify wildcard teams
        conference_teams = self._get_conference_teams(standings_data, conference)
        wildcard_teams = [
            team for team in conference_teams
            if team.team_id not in [dw.team_id for dw in division_winners]
        ]

        # Step 4: Sort wildcards by record (seeds 5-7)
        wildcard_teams = self._sort_teams_by_record(wildcard_teams)[:3]

        # Step 5: Create playoff seeds
        seeds = []
        for i, team in enumerate(division_winners + wildcard_teams, start=1):
            seed = self._create_playoff_seed(
                team=team,
                seed=i,
                conference=conference,
                is_division_winner=(i <= 4)
            )
            seeds.append(seed)

        # Step 6: Determine clinched/eliminated
        # For MVP: Simple logic - top 7 clinched, rest eliminated
        # Future: Implement proper clinching/elimination scenarios
        clinched = [seed.team_id for seed in seeds]
        all_conference_teams = [t.team_id for t in conference_teams]
        eliminated = [tid for tid in all_conference_teams if tid not in clinched]

        return ConferenceSeeding(
            conference=conference,
            seeds=seeds,
            division_winners=seeds[:4],
            wildcards=seeds[4:],
            clinched_teams=clinched,
            eliminated_teams=eliminated
        )

    def _get_division_winners(
        self,
        standings_data: Dict[int, EnhancedTeamStanding],
        conference: str
    ) -> List[EnhancedTeamStanding]:
        """
        Get the leader from each division in the conference.

        Args:
            standings_data: Dict of team standings
            conference: 'AFC' or 'NFC'

        Returns:
            List of 4 division winners
        """
        division_winners = []

        for division_name, team_ids in NFL_DIVISIONS.items():
            # Only process divisions in this conference
            if conference not in division_name:
                continue

            # Get standings for teams in this division
            division_teams = [
                standings_data[tid] for tid in team_ids
                if tid in standings_data
            ]

            # Sort by record and take leader
            if division_teams:
                sorted_teams = self._sort_teams_by_record(division_teams)
                leader = sorted_teams[0]
                division_winners.append(leader)

        return division_winners

    def _get_conference_teams(
        self,
        standings_data: Dict[int, EnhancedTeamStanding],
        conference: str
    ) -> List[EnhancedTeamStanding]:
        """
        Get all teams in a conference sorted by record.

        Args:
            standings_data: Dict of team standings
            conference: 'AFC' or 'NFC'

        Returns:
            List of all conference teams sorted by record
        """
        if conference == 'AFC':
            team_ids = range(1, 17)
        else:  # NFC
            team_ids = range(17, 33)

        conference_teams = [
            standings_data[tid] for tid in team_ids
            if tid in standings_data
        ]

        return self._sort_teams_by_record(conference_teams)

    def _sort_teams_by_record(
        self,
        teams: List[EnhancedTeamStanding]
    ) -> List[EnhancedTeamStanding]:
        """
        Sort teams by NFL tiebreaker rules.

        Tiebreaker order:
        1. Win percentage (primary)
        2. Total wins (secondary)
        3. Conference record (tertiary)
        4. Division record (quaternary)
        5. Point differential
        6. Points scored

        Future Enhancement: Implement full NFL tiebreaker rules:
        - Head-to-head record
        - Common games
        - Strength of victory
        - Strength of schedule
        - Net points in conference games
        - Coin toss

        Args:
            teams: List of team standings

        Returns:
            Sorted list (best to worst)
        """
        return sorted(
            teams,
            key=lambda t: (
                t.win_percentage,       # 1. Win percentage
                t.wins,                  # 2. Total wins
                t.conference_wins,       # 3. Conference record
                t.division_wins,         # 4. Division record
                t.point_differential,    # 5. Point differential
                t.points_for             # 6. Points scored
            ),
            reverse=True
        )

    def _create_playoff_seed(
        self,
        team: EnhancedTeamStanding,
        seed: int,
        conference: str,
        is_division_winner: bool
    ) -> PlayoffSeed:
        """
        Create a PlayoffSeed from team standing.

        Args:
            team: Team standing data
            seed: Seed number (1-7)
            conference: 'AFC' or 'NFC'
            is_division_winner: True for seeds 1-4

        Returns:
            PlayoffSeed object
        """
        # Determine division name
        division_name = self._get_team_division(team.team_id)

        return PlayoffSeed(
            seed=seed,
            team_id=team.team_id,
            wins=team.wins,
            losses=team.losses,
            ties=team.ties,
            win_percentage=team.win_percentage,
            division_winner=is_division_winner,
            division_name=division_name,
            conference=conference,
            points_for=team.points_for,
            points_against=team.points_against,
            point_differential=team.point_differential,
            division_record=team.division_record,
            conference_record=team.conference_record,
            tiebreaker_notes=None  # Future: Add tiebreaker details
        )

    def _get_team_division(self, team_id: int) -> str:
        """
        Get division name for a team.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Division name (e.g., "AFC East")
        """
        for division_name, team_ids in NFL_DIVISIONS.items():
            if team_id in team_ids:
                return division_name
        return "Unknown"
