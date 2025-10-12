"""
Mock Standings Generator

Generates fake regular season standings data for testing playoff initialization
without running a full season simulation.
"""

import random
from typing import Dict
from stores.standings_store import EnhancedTeamStanding


class MockStandingsGenerator:
    """Generate realistic mock standings for playoff testing."""

    # NFL Division structure
    DIVISIONS = {
        'AFC East': [1, 2, 3, 4],          # Bills, Dolphins, Patriots, Jets
        'AFC North': [5, 6, 7, 8],         # Ravens, Bengals, Browns, Steelers
        'AFC South': [9, 10, 11, 12],      # Texans, Colts, Jaguars, Titans
        'AFC West': [13, 14, 15, 16],      # Chiefs, Raiders, Chargers, Broncos
        'NFC East': [17, 18, 19, 20],      # Cowboys, Giants, Eagles, Commanders
        'NFC North': [21, 22, 23, 24],     # Bears, Lions, Packers, Vikings
        'NFC South': [25, 26, 27, 28],     # Falcons, Panthers, Saints, Buccaneers
        'NFC West': [29, 30, 31, 32]       # Cardinals, Rams, 49ers, Seahawks
    }

    def __init__(self, seed: int = None):
        """
        Initialize generator with optional random seed.

        Args:
            seed: Random seed for reproducible testing
        """
        if seed is not None:
            random.seed(seed)

    def generate_standings(self) -> Dict[int, EnhancedTeamStanding]:
        """
        Generate complete standings for all 32 NFL teams.

        Creates realistic records with:
        - 4 division winners per conference (better records)
        - 3 wild card teams per conference
        - Random records weighted by division placement

        Returns:
            Dict mapping team_id -> EnhancedTeamStanding
        """
        standings = {}

        for division_name, team_ids in self.DIVISIONS.items():
            # Generate division standings (1st place gets best record)
            division_standings = self._generate_division_standings(
                team_ids=team_ids,
                division_name=division_name
            )
            standings.update(division_standings)

        return standings

    def _generate_division_standings(
        self,
        team_ids: list,
        division_name: str
    ) -> Dict[int, EnhancedTeamStanding]:
        """
        Generate standings for one division.

        Args:
            team_ids: List of 4 team IDs in this division
            division_name: Division name (e.g., "AFC East")

        Returns:
            Dict of team_id -> EnhancedTeamStanding for this division
        """
        # Generate base records (1st place gets most wins)
        base_wins = [
            random.randint(12, 14),  # 1st place
            random.randint(9, 11),   # 2nd place
            random.randint(7, 9),    # 3rd place
            random.randint(4, 6)     # 4th place
        ]

        # Shuffle to randomize division order
        teams_with_wins = list(zip(team_ids, base_wins))
        random.shuffle(teams_with_wins)

        standings = {}
        for place, (team_id, wins) in enumerate(teams_with_wins, 1):
            losses = 17 - wins  # 17-game season
            ties = 0

            # Generate other stats
            division_wins = random.randint(2, 6)
            division_losses = 6 - division_wins
            conf_wins = random.randint(6, 12)
            conf_losses = min(12 - conf_wins, losses)

            points_for = random.randint(300, 500)
            points_against = random.randint(300, 500)

            # Create standing
            standing = EnhancedTeamStanding(
                team_id=team_id,
                wins=wins,
                losses=losses,
                ties=ties,
                division_wins=division_wins,
                division_losses=division_losses,
                conference_wins=conf_wins,
                conference_losses=conf_losses,
                home_wins=random.randint(4, 8),
                home_losses=9 - random.randint(4, 8),
                away_wins=random.randint(3, 7),
                away_losses=9 - random.randint(3, 7),
                points_for=points_for,
                points_against=points_against,
                streak=f"W{random.randint(1, 3)}" if random.random() > 0.5 else f"L{random.randint(1, 3)}",
                division_place=place
            )

            standings[team_id] = standing

        return standings

    def print_standings_summary(self, standings: Dict[int, EnhancedTeamStanding]):
        """
        Print a summary of generated standings.

        Args:
            standings: Complete standings dict
        """
        print("\n" + "="*80)
        print("MOCK STANDINGS GENERATED".center(80))
        print("="*80)

        for division_name, team_ids in self.DIVISIONS.items():
            print(f"\n{division_name}:")
            division_teams = [(tid, standings[tid]) for tid in team_ids]
            # Sort by wins
            division_teams.sort(key=lambda x: (-x[1].wins, x[1].losses))

            for team_id, standing in division_teams:
                print(f"  Team {team_id:2d}: {standing.wins:2d}-{standing.losses:2d}-{standing.ties} "
                      f"({standing.win_percentage:.3f}) - "
                      f"PF: {standing.points_for}, PA: {standing.points_against}")

        print("="*80)


if __name__ == "__main__":
    # Test the generator
    generator = MockStandingsGenerator(seed=42)
    standings = generator.generate_standings()
    generator.print_standings_summary(standings)

    # Verify we have 32 teams
    print(f"\n✓ Generated {len(standings)} team standings")

    # Verify all team IDs are present
    missing = set(range(1, 33)) - set(standings.keys())
    if missing:
        print(f"❌ Missing team IDs: {missing}")
    else:
        print("✓ All 32 teams present")
