#!/usr/bin/env python3
"""
Random Playoff Seeder

Generates random but realistic playoff seeding scenarios for testing and demonstration.

This module creates randomized playoff scenarios by:
1. Selecting 14 random teams (7 AFC, 7 NFC)
2. Generating realistic season records (10-7 to 15-2 range)
3. Creating complete standings data with realistic stats
4. Using PlayoffSeeder to calculate proper seeding with tiebreakers

The generated scenarios are useful for:
- Testing playoff bracket generation
- Demonstrating playoff seeder functionality
- Creating diverse playoff scenarios for UI testing
- Validating tiebreaker logic

Run: PYTHONPATH=src python demo/interactive_playoff_sim/random_playoff_seeder.py
"""

import random
from typing import Dict, List
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from constants.team_ids import TeamIDs
from stores.standings_store import EnhancedTeamStanding
from playoff_system.playoff_seeder import PlayoffSeeder
from playoff_system.seeding_models import PlayoffSeeding


class RandomPlayoffSeeder:
    """
    Generates random but realistic playoff scenarios.

    Creates standings data for 14 playoff teams with realistic records
    and statistical distributions that match NFL norms.
    """

    def __init__(self, seed: int = None):
        """
        Initialize random playoff seeder.

        Args:
            seed: Optional random seed for reproducibility
        """
        if seed is not None:
            random.seed(seed)

        self.seeder = PlayoffSeeder()

    def generate_random_seeding(
        self,
        season: int = 2024,
        week: int = 18,
        min_wins: int = 10,
        max_wins: int = 15
    ) -> PlayoffSeeding:
        """
        Generate a random playoff seeding scenario.

        Args:
            season: Season year (default: 2024)
            week: Week number (default: 18 - end of regular season)
            min_wins: Minimum wins for playoff teams (default: 10)
            max_wins: Maximum wins for playoff teams (default: 15)

        Returns:
            PlayoffSeeding object with random but realistic playoff bracket
        """
        # Validate inputs
        if min_wins < 7 or max_wins > 17:
            raise ValueError("Win range must be between 7 and 17 games")
        if min_wins >= max_wins:
            raise ValueError("min_wins must be less than max_wins")

        # Select random playoff teams
        afc_teams = self._select_random_teams('AFC', count=7)
        nfc_teams = self._select_random_teams('NFC', count=7)

        # Generate standings for all 32 teams (playoff teams + non-playoff teams)
        standings = self._generate_standings(
            playoff_teams={'AFC': afc_teams, 'NFC': nfc_teams},
            min_wins=min_wins,
            max_wins=max_wins
        )

        # Calculate official seeding using PlayoffSeeder
        return self.seeder.calculate_seeding(standings, season=season, week=week)

    def _select_random_teams(self, conference: str, count: int = 7) -> List[int]:
        """
        Select random teams from a conference.

        Args:
            conference: 'AFC' or 'NFC'
            count: Number of teams to select (default: 7 for playoffs)

        Returns:
            List of team IDs
        """
        conference_teams = TeamIDs.get_conference_teams(conference)
        return random.sample(conference_teams, count)

    def _generate_standings(
        self,
        playoff_teams: Dict[str, List[int]],
        min_wins: int,
        max_wins: int
    ) -> Dict[int, EnhancedTeamStanding]:
        """
        Generate realistic standings for all 32 NFL teams.

        Playoff teams get records in the specified win range.
        Non-playoff teams get weaker records (3-9 wins typically).

        Args:
            playoff_teams: Dict with 'AFC' and 'NFC' lists of playoff team IDs
            min_wins: Minimum wins for playoff teams
            max_wins: Maximum wins for playoff teams

        Returns:
            Dictionary mapping team_id to EnhancedTeamStanding
        """
        standings = {}
        all_playoff_teams = playoff_teams['AFC'] + playoff_teams['NFC']

        for team_id in range(1, 33):
            is_playoff_team = team_id in all_playoff_teams

            if is_playoff_team:
                # Playoff teams: Strong records (min_wins to max_wins)
                wins = random.randint(min_wins, max_wins)
            else:
                # Non-playoff teams: Weaker records (3-9 wins typically)
                wins = random.randint(3, 9)

            # Calculate losses (17-game season)
            losses = 17 - wins

            # Generate realistic statistics
            standing = self._create_realistic_standing(
                team_id=team_id,
                wins=wins,
                losses=losses,
                is_playoff_team=is_playoff_team
            )

            standings[team_id] = standing

        return standings

    def _create_realistic_standing(
        self,
        team_id: int,
        wins: int,
        losses: int,
        is_playoff_team: bool
    ) -> EnhancedTeamStanding:
        """
        Create a realistic team standing with appropriate statistics.

        Generates points for/against, division/conference records that
        correlate with the team's overall record and playoff status.

        Args:
            team_id: NFL team ID (1-32)
            wins: Number of wins
            losses: Number of losses
            is_playoff_team: True if this is a playoff team

        Returns:
            EnhancedTeamStanding with realistic data
        """
        games_played = wins + losses

        # Calculate realistic points scored/allowed
        # Better teams score more, allow less
        win_percentage = wins / games_played if games_played > 0 else 0

        # Base points per game (NFL average ~22-24 points)
        base_ppg = 22.0

        # Playoff teams generally score more and allow less
        if is_playoff_team:
            ppg_modifier = 1.0 + (win_percentage - 0.5) * 0.6  # Range: ~0.7 to 1.3
            points_for = int(base_ppg * ppg_modifier * games_played + random.randint(-30, 30))
            points_against = int(base_ppg * (2.0 - ppg_modifier) * games_played + random.randint(-30, 30))
        else:
            # Non-playoff teams have more variance
            ppg_modifier = 0.7 + win_percentage * 0.6  # Range: ~0.7 to 1.3
            points_for = int(base_ppg * ppg_modifier * games_played + random.randint(-40, 40))
            points_against = int(base_ppg * (2.0 - ppg_modifier) * games_played + random.randint(-40, 40))

        # Ensure realistic minimums
        points_for = max(150, min(550, points_for))
        points_against = max(150, min(550, points_against))

        # Generate division record (6 division games per season)
        division_games = 6
        # Division win rate roughly correlates with overall win rate
        division_win_rate = win_percentage + random.uniform(-0.15, 0.15)
        division_win_rate = max(0, min(1, division_win_rate))
        division_wins = int(division_games * division_win_rate)
        division_losses = division_games - division_wins

        # Generate conference record (roughly 12-13 conference games)
        conference_games = 13
        conference_win_rate = win_percentage + random.uniform(-0.1, 0.1)
        conference_win_rate = max(0, min(1, conference_win_rate))
        conference_wins = int(conference_games * conference_win_rate)
        conference_losses = conference_games - conference_wins

        # Generate home/away splits
        home_games = 9
        away_games = 8
        home_win_rate = win_percentage + 0.1  # Home field advantage
        home_win_rate = max(0, min(1, home_win_rate))
        home_wins = min(home_games, int(home_games * home_win_rate))
        home_losses = home_games - home_wins

        away_wins = wins - home_wins
        away_losses = away_games - away_wins

        # Ensure away stats are non-negative
        if away_wins < 0:
            away_wins = 0
            home_wins = wins
            home_losses = home_games - home_wins

        return EnhancedTeamStanding(
            team_id=team_id,
            wins=wins,
            losses=losses,
            ties=0,  # Ties are rare in modern NFL
            division_wins=division_wins,
            division_losses=division_losses,
            conference_wins=conference_wins,
            conference_losses=conference_losses,
            home_wins=home_wins,
            home_losses=home_losses,
            away_wins=away_wins,
            away_losses=away_losses,
            points_for=points_for,
            points_against=points_against,
            streak="",  # Not needed for seeding calculation
            last_5=""   # Not needed for seeding calculation
        )


def demo_random_seeding():
    """Demonstrate random playoff seeding generation."""
    from team_management.teams.team_loader import get_team_by_id

    print("=" * 100)
    print("RANDOM PLAYOFF SEEDER DEMO".center(100))
    print("=" * 100)
    print()

    # Generate random seeding
    print("Generating random playoff scenario...")
    generator = RandomPlayoffSeeder(seed=42)  # Use seed for reproducibility in demo
    seeding = generator.generate_random_seeding(season=2024, week=18)

    print(f"Season: {seeding.season}, Week: {seeding.week}")
    print()

    # Display AFC seeding
    print("-" * 100)
    print("AFC PLAYOFF SEEDING")
    print("-" * 100)
    for seed_obj in seeding.afc.seeds:
        team = get_team_by_id(seed_obj.team_id)
        status = "DIV" if seed_obj.division_winner else "WC"
        bye = " (BYE)" if seed_obj.seed == 1 else ""
        print(f"  {seed_obj.seed}. [{status}] {team.full_name:32} {seed_obj.record_string:8} "
              f"PF: {seed_obj.points_for:3}  PA: {seed_obj.points_against:3}  "
              f"Diff: {seed_obj.point_differential:+4}{bye}")

    print()

    # Display NFC seeding
    print("-" * 100)
    print("NFC PLAYOFF SEEDING")
    print("-" * 100)
    for seed_obj in seeding.nfc.seeds:
        team = get_team_by_id(seed_obj.team_id)
        status = "DIV" if seed_obj.division_winner else "WC"
        bye = " (BYE)" if seed_obj.seed == 1 else ""
        print(f"  {seed_obj.seed}. [{status}] {team.full_name:32} {seed_obj.record_string:8} "
              f"PF: {seed_obj.points_for:3}  PA: {seed_obj.points_against:3}  "
              f"Diff: {seed_obj.point_differential:+4}{bye}")

    print()
    print("=" * 100)
    print()

    # Show potential matchups
    print("WILD CARD ROUND MATCHUPS")
    print("-" * 100)
    matchups = seeding.get_matchups()

    print("\nAFC Wild Card Games:")
    for i, (home_id, away_id) in enumerate(matchups['AFC'], start=1):
        home_team = get_team_by_id(home_id)
        away_team = get_team_by_id(away_id)
        home_seed = seeding.get_seed(home_id)
        away_seed = seeding.get_seed(away_id)
        print(f"  Game {i}: ({away_seed.seed}) {away_team.full_name} @ "
              f"({home_seed.seed}) {home_team.full_name}")

    print("\nNFC Wild Card Games:")
    for i, (home_id, away_id) in enumerate(matchups['NFC'], start=1):
        home_team = get_team_by_id(home_id)
        away_team = get_team_by_id(away_id)
        home_seed = seeding.get_seed(home_id)
        away_seed = seeding.get_seed(away_id)
        print(f"  Game {i}: ({away_seed.seed}) {away_team.full_name} @ "
              f"({home_seed.seed}) {home_team.full_name}")

    print()
    print("=" * 100)
    print("Random playoff seeding generated successfully!".center(100))
    print("=" * 100)


if __name__ == "__main__":
    try:
        demo_random_seeding()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
